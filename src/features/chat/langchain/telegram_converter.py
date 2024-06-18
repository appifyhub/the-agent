from langchain_core.messages import HumanMessage, AIMessage

from db.schema.chat_message import ChatMessage
from db.schema.user import User
from util.config import config
from util.functions import is_the_agent
from util.safe_printer_mixin import SafePrinterMixin


class TelegramConverter(SafePrinterMixin):

    def __init__(self):
        super().__init__(config.verbose)

    def convert(self, author: User | None, message: ChatMessage) -> HumanMessage | AIMessage:
        self.sprint(f"Converting {message} by {author} to LangChain message")
        content = self.__convert_message_text(author, message)
        if not author or is_the_agent(author):
            return AIMessage(content)
        return HumanMessage(content)

    def __convert_message_text(self, author: User | None, message: ChatMessage) -> str:
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
        self.sprint(f"Converted message parts: {parts}")
        return "\n".join(parts)
