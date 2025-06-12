from enum import Enum

from db.crud.user import UserCRUD
from db.schema.user import User
from api.settings_controller import SettingsController
from features.chat.sponsorship_manager import SponsorshipManager
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.prompting.prompt_library import TELEGRAM_BOT_USER
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

COMMAND_START = "start"
COMMAND_SETTINGS = "settings"


class CommandProcessor(SafePrinterMixin):
    class Result(Enum):
        failed = "Failed"
        unknown = "Unknown"
        success = "Success"

    __invoker: User
    __user_dao: UserCRUD
    __sponsorship_manager: SponsorshipManager
    __settings_controller: SettingsController
    __telegram_sdk: TelegramBotSDK

    def __init__(
        self,
        invoker: User,
        user_dao: UserCRUD,
        sponsorship_manager: SponsorshipManager,
        settings_controller: SettingsController,
        telegram_sdk: TelegramBotSDK,
    ):
        super().__init__(config.verbose)
        self.__invoker = invoker
        self.__user_dao = user_dao
        self.__sponsorship_manager = sponsorship_manager
        self.__settings_controller = settings_controller
        self.__telegram_sdk = telegram_sdk

    def execute(self, raw_input: str) -> Result:
        self.sprint(f"Starting to evaluate command input '{raw_input}'")
        try:
            if not raw_input:
                self.sprint("Nothing to process")
                return CommandProcessor.Result.unknown
            command_parts = raw_input.split()
            if command_parts and command_parts[0].startswith("/"):
                # bot is sometimes tagged like this: /start@my_bot
                full_command_with_tag = command_parts[0]  # discard command arguments
                core_command: str
                if "@" in full_command_with_tag:
                    core_command, bot_tag = full_command_with_tag.split("@")
                    if bot_tag != TELEGRAM_BOT_USER.telegram_username:
                        self.sprint("Unknown bot tagged")
                        return CommandProcessor.Result.unknown
                else:
                    core_command = full_command_with_tag
                command_name = core_command[1:]
                command_args = command_parts[1:]
                if command_name in [COMMAND_START, COMMAND_SETTINGS]:
                    return self.__handle_config_commands(command_name, command_args)
            self.sprint("No known command found")
            return CommandProcessor.Result.unknown
        except Exception as e:
            self.sprint("Failed to process command", e)
            return CommandProcessor.Result.failed

    def __handle_config_commands(self, command_name: str, command_args: list[str]) -> Result:
        self.sprint(f"Processing the config command '{command_name}' and args '{command_args}'")
        try:
            if command_name == COMMAND_START:
                # try to accept a sponsorship (works if this is the first message and user is pre-sponsored)
                accepted_sponsorship = self.__sponsorship_manager.accept_sponsorship(self.__invoker)
                if accepted_sponsorship:
                    self.sprint("Accepted a sponsorship by messaging the bot")
                    return CommandProcessor.Result.success
            # no sponsorship accepted, so let's share the settings link
            link_url = self.__settings_controller.create_settings_link()
            self.__telegram_sdk.send_button_link(self.__invoker.telegram_chat_id, link_url)
            self.sprint("Shared the settings link with the user")
            return CommandProcessor.Result.success
        except Exception as e:
            self.sprint("Failed to process the command", e)
            return CommandProcessor.Result.failed
