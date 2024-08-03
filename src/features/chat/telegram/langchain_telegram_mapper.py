from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage

from db.schema.chat_message import ChatMessage, ChatMessageSave
from db.schema.user import User
from features.chat.telegram.telegram_chat_bot import TELEGRAM_BOT_USER
from features.llm.predefined_prompts import MULTI_MESSAGE_DELIMITER
from util.config import config
from util.functions import is_the_agent, construct_bot_message_id
from util.safe_printer_mixin import SafePrinterMixin


class LangChainTelegramMapper(SafePrinterMixin):

    def __init__(self):
        super().__init__(config.verbose)

    def map_to_langchain(self, author: User | None, message: ChatMessage) -> HumanMessage | AIMessage:
        self.sprint(f"Converting {message} by {author} to LangChain message")
        content = self.__convert_stored_message_text(author, message)
        if not author or is_the_agent(author):
            return AIMessage(content)
        return HumanMessage(content)

    def map_bot_message_to_storage(self, chat_id: str, message: AIMessage) -> list[ChatMessageSave]:
        self.sprint(f"Converting AI message '{message}' to storage message")
        result: list[ChatMessageSave] = []
        content = self.__convert_bot_message_text(message)
        parts = content.split(MULTI_MESSAGE_DELIMITER)
        for part in parts:
            if not part: continue
            sent_at = datetime.now()
            storage_message = ChatMessageSave(
                chat_id = chat_id,
                message_id = construct_bot_message_id(chat_id, sent_at),
                author_id = TELEGRAM_BOT_USER.id,
                sent_at = sent_at,
                text = part,
            )
            result.append(storage_message)
        return result

    def __convert_stored_message_text(self, author: User | None, message: ChatMessage) -> str:
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
        self.sprint(f"Converted message parts: {parts}, joining...")
        return "\n".join(parts)

    def __convert_bot_message_text(self, message: AIMessage) -> str:
        self.sprint(f"Converting AI message {message}")
        # content can be either a list (of strings or dicts) or a plain string
        if not message.content:
            return ""
        if isinstance(message.content, str):
            return message.content
        if isinstance(message.content[0], str):
            return MULTI_MESSAGE_DELIMITER.join(message.content)
        pretty_print = lambda raw_dict: "\n".join(f"{key}: {value}" for key, value in raw_dict.items())
        pretty_dicts = [pretty_print(raw_dict) for raw_dict in message.content]
        return MULTI_MESSAGE_DELIMITER.join(pretty_dicts)
