import random
from datetime import datetime
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage

from db.model.chat_config import ChatConfigDB
from db.schema.chat_config import ChatConfig
from db.schema.chat_message import ChatMessage, ChatMessageSave
from db.schema.user import User
from features.integrations.integrations import is_the_agent, resolve_agent_user, resolve_external_handle, resolve_external_id
from features.prompting.prompt_library import CHAT_MESSAGE_DELIMITER
from util import log


class DomainLangchainMapper:

    def map_to_langchain(
        self,
        author: User | None,
        message: ChatMessage,
        chat_type: ChatConfigDB.ChatType,
    ) -> HumanMessage | AIMessage:
        log.t(f"Mapping {message.message_id} by {author.id.hex if author else '<unknown>'} to Langchain message")
        content = self.__map_stored_message_text(author, message, chat_type)
        if not author or is_the_agent(author, chat_type):
            return AIMessage(content)
        return HumanMessage(content)

    def map_bot_message_to_storage(self, chat: ChatConfig, message: AIMessage) -> list[ChatMessageSave]:
        log.t(f"Mapping AI message '{message}' to storage message")
        result: list[ChatMessageSave] = []
        content = self.__map_bot_message_text(message)
        parts = content.split(CHAT_MESSAGE_DELIMITER)
        for part in parts:
            if not part:
                continue
            sent_at = datetime.now()
            agent_user = resolve_agent_user(chat.chat_type)
            storage_message = ChatMessageSave(
                chat_id = chat.chat_id,
                message_id = DomainLangchainMapper.__construct_bot_message_id(chat.chat_id, sent_at),  # unused outside
                author_id = agent_user.id,
                sent_at = sent_at,
                text = part,
            )
            result.append(storage_message)
        return result

    # noinspection PyMethodMayBeStatic
    def __map_stored_message_text(self, author: User | None, message: ChatMessage, chat_type: ChatConfigDB.ChatType) -> str:
        parts = []
        if author:
            name_parts = []
            if platform_handle := resolve_external_handle(author, chat_type):
                name_parts.append(f"@{platform_handle}")
            if author.full_name:
                name_parts.append(f"[{author.full_name}]")
            if not name_parts and (platform_user_id := resolve_external_id(author, chat_type)):
                name_parts.append(f"#UID-{platform_user_id}")
            if not is_the_agent(author, chat_type):
                name_tag = " ".join(name_parts)
                parts.append(f"{name_tag}:")
        parts.append(message.text)
        log.t(f"  Mapped message parts: {parts}, joining...")
        return "\n".join(parts)

    # noinspection PyMethodMayBeStatic
    def __map_bot_message_text(self, message: AIMessage) -> str:
        log.t(f"  Mapping AI message {message}")

        def pretty_print(raw_dict):
            return "\n".join(f"{key}: {value}" for key, value in raw_dict.items())

        # edge: no content
        if not message.content:
            return ""
        # main: plain string
        if isinstance(message.content, str):
            return message.content
        # edge: it's a dict
        if isinstance(message.content, dict):
            return pretty_print(message.content)
        # edge: it's a list
        if isinstance(message.content, list):
            messages: list[str] = []
            for item in message.content:
                if isinstance(item, str):
                    messages.append(item)
                elif isinstance(item, dict):
                    messages.append(pretty_print(item))
                else:
                    messages.append(str(item))
            return CHAT_MESSAGE_DELIMITER.join(messages)
        # noinspection PyUnreachableCode
        return str(message.content)

    @staticmethod
    def __construct_bot_message_id(chat_id: UUID, sent_at: datetime) -> str:
        random_seed = str(random.randint(1000, 9999))
        formatted_time = sent_at.strftime("%y%m%d%H%M%S")
        result = f"{chat_id}-{formatted_time}-{random_seed}"
        return result
