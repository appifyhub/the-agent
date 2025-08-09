from datetime import datetime
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage

from db.schema.chat_message import ChatMessage, ChatMessageSave
from db.schema.user import User
from features.prompting.prompt_library import MULTI_MESSAGE_DELIMITER, TELEGRAM_BOT_USER
from util import log
from util.functions import construct_bot_message_id, is_the_agent


class DomainLangchainMapper:

    def map_to_langchain(self, author: User | None, message: ChatMessage) -> HumanMessage | AIMessage:
        log.d(f"Mapping {message} by {author} to Langchain message")
        content = self.__map_stored_message_text(author, message)
        if not author or is_the_agent(author):
            return AIMessage(content)
        return HumanMessage(content)

    def map_bot_message_to_storage(self, chat_id: UUID, message: AIMessage) -> list[ChatMessageSave]:
        log.d(f"Mapping AI message '{message}' to storage message")
        result: list[ChatMessageSave] = []
        content = self.__map_bot_message_text(message)
        parts = content.split(MULTI_MESSAGE_DELIMITER)
        for part in parts:
            if not part:
                continue
            sent_at = datetime.now()
            storage_message = ChatMessageSave(
                chat_id = chat_id,
                message_id = construct_bot_message_id(chat_id, sent_at),  # irrelevant outside
                author_id = TELEGRAM_BOT_USER.id,
                sent_at = sent_at,
                text = part,
            )
            result.append(storage_message)
        return result

    # noinspection PyMethodMayBeStatic
    def __map_stored_message_text(self, author: User | None, message: ChatMessage) -> str:
        parts = []
        if author:
            name_parts = []
            if author.telegram_username:
                name_parts.append(f"@{author.telegram_username}")
            if author.full_name:
                name_parts.append(f"[{author.full_name}]")
            if not name_parts and author.telegram_user_id:
                name_parts.append(f"@{author.telegram_user_id}")
            if not is_the_agent(author):
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
            return MULTI_MESSAGE_DELIMITER.join(messages)
        return str(message.content)
