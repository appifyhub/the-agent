from enum import Enum

from db.crud.chat_config import ChatConfigCRUD
from db.schema.chat_config import ChatConfig, ChatConfigSave
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


class ChatConfigManager(SafePrinterMixin):
    class Result(Enum):
        success = "success"
        failure = "failure"

    __chat_config_dao: ChatConfigCRUD

    def __init__(self, chat_config_dao: ChatConfigCRUD):
        super().__init__(config.verbose)
        self.__chat_config_dao = chat_config_dao

    def change_chat_language(
        self,
        chat_id: str,
        language_name: str,
        language_iso_code: str | None = None,
    ) -> tuple[Result, str]:
        self.sprint(f"Changing language for chat '{chat_id}' to '{language_name}' ({language_iso_code})")

        chat_config_db = self.__chat_config_dao.get(chat_id)
        if not chat_config_db:
            message = f"Chat '{chat_id}' not found"
            self.sprint(message)
            return ChatConfigManager.Result.failure, message

        chat_config = ChatConfig.model_validate(chat_config_db)
        chat_config.language_name = language_name
        chat_config.language_iso_code = language_iso_code
        chat_config_db = self.__chat_config_dao.save(ChatConfigSave(**chat_config.model_dump()))
        chat_config = ChatConfig.model_validate(chat_config_db)

        language_display: str | None
        if not chat_config.language_name and not chat_config.language_iso_code:
            language_display = None
        elif not chat_config.language_name:
            language_display = f"ISO: '{chat_config.language_iso_code.upper()}'"
        elif not chat_config.language_iso_code:
            language_display = chat_config.language_name.capitalize()
        else:
            language_display = f"{chat_config.language_name.capitalize()} ('{chat_config.language_iso_code.upper()}')"

        message = f"Chat language changed to {language_display}"
        self.sprint(message)
        return ChatConfigManager.Result.success, message

    def change_chat_reply_chance(self, chat_id: str, reply_chance_percent: int) -> tuple[Result, str]:
        self.sprint(f"Changing reply chance for chat '{chat_id}' to '{reply_chance_percent}%'")

        if reply_chance_percent < 0 or reply_chance_percent > 100:
            message = "Invalid reply chance percent, must be in [0-100]"
            self.sprint(message)
            return ChatConfigManager.Result.failure, message

        chat_config_db = self.__chat_config_dao.get(chat_id)
        if not chat_config_db:
            message = f"Chat '{chat_id}' not found"
            self.sprint(message)
            return ChatConfigManager.Result.failure, message

        chat_config = ChatConfig.model_validate(chat_config_db)
        if chat_config.is_private:
            message = "Chat is private, reply chance cannot be changed"
            self.sprint(message)
            return ChatConfigManager.Result.failure, message

        chat_config.reply_chance_percent = reply_chance_percent
        chat_config_db = self.__chat_config_dao.save(ChatConfigSave(**chat_config.model_dump()))
        chat_config = ChatConfig.model_validate(chat_config_db)

        message = f"Reply chance is now set to {chat_config.reply_chance_percent}%"
        self.sprint(message)
        return ChatConfigManager.Result.success, message
