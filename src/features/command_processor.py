from enum import Enum

from db.crud.user import UserCRUD
from db.schema.user import User, UserSave
from features.prompting.predefined_prompts import COMMAND_START, TELEGRAM_BOT_USER
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


class CommandProcessor(SafePrinterMixin):
    class Result(Enum):
        failed = "Failed"
        unknown = "Unknown"
        success = "Success"

    __invoker: User
    __user_dao: UserCRUD

    def __init__(self, invoker: User, user_dao: UserCRUD):
        super().__init__(config.verbose)
        self.__invoker = invoker
        self.__user_dao = user_dao

    def execute(self, raw_input: str) -> Result:
        self.sprint(f"Starting to evaluate command input '{raw_input}'")
        try:
            if not raw_input:
                self.sprint("Nothing to process")
                return CommandProcessor.Result.unknown
            command_parts = raw_input.split()
            if command_parts and command_parts[0].startswith(f"/"):
                full_command = command_parts[0]
                core_command = full_command
                if "@" in full_command:
                    core_command, bot_tag = full_command.split("@")
                    if bot_tag != TELEGRAM_BOT_USER.telegram_username:
                        self.sprint("Unknown bot tagged")
                        return CommandProcessor.Result.unknown
                if core_command[1:] == COMMAND_START:
                    return self.__handle_start_command(command_parts[1:])
            self.sprint("No known command found")
            return CommandProcessor.Result.unknown
        except Exception as e:
            self.sprint("Failed to process command", e)
            return CommandProcessor.Result.failed

    def __handle_start_command(self, parts: list[str]) -> Result:
        self.sprint(f"Processing OpenAI key now from parts [{", ".join(parts)}]")
        try:
            if not parts:
                self.sprint("Not enough command parts")
                return CommandProcessor.Result.unknown
            self.__user_dao.save(
                UserSave(
                    id = self.__invoker.id,
                    full_name = self.__invoker.full_name,
                    telegram_username = self.__invoker.telegram_username,
                    telegram_chat_id = self.__invoker.telegram_chat_id,
                    telegram_user_id = self.__invoker.telegram_user_id,
                    open_ai_key = parts[0],
                    group = self.__invoker.group,
                )
            )
            return CommandProcessor.Result.success
        except Exception as e:
            self.sprint(f"Failed to process OpenAI key", e)
            return CommandProcessor.Result.failed
