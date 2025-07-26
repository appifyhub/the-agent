from enum import Enum

from di.di import DI
from features.prompting.prompt_library import TELEGRAM_BOT_USER
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

COMMAND_START = "start"
COMMAND_SETTINGS = "settings"
COMMAND_HELP = "help"
SUPPORTED_COMMANDS = [COMMAND_START, COMMAND_SETTINGS, COMMAND_HELP]


class CommandProcessor(SafePrinterMixin):
    class Result(Enum):
        failed = "Failed"
        unknown = "Unknown"
        success = "Success"

    __di: DI

    def __init__(self, di: DI):
        super().__init__(config.verbose)
        self.__di = di

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
                if command_name in SUPPORTED_COMMANDS:
                    return self.__handle_config_commands(command_name, command_args)
            self.sprint("No known command found")
            return CommandProcessor.Result.unknown
        except Exception as e:
            self.sprint("Failed to process command", e)
            return CommandProcessor.Result.failed

    def __handle_config_commands(self, command_name: str, command_args: list[str]) -> Result:
        self.sprint(f"Processing the config command '{command_name}' and args '{command_args}'")
        try:
            if command_name in [COMMAND_START, COMMAND_SETTINGS]:
                # try to accept a sponsorship (works if this is the first message and user is pre-sponsored)
                if command_name == COMMAND_START:
                    if self.__di.sponsorship_service.accept_sponsorship(self.__di.invoker):
                        self.sprint("Accepted a sponsorship by messaging the bot")
                        return CommandProcessor.Result.success
                # no sponsorship accepted, so let's share the settings link
                settings_url = self.__di.settings_controller.create_settings_link()
                self.__di.telegram_bot_sdk.send_button_link(self.__di.invoker.telegram_chat_id, settings_url)
                self.sprint("Shared the settings link with the user")
                return CommandProcessor.Result.success

            if command_name == COMMAND_HELP:
                # share the help link
                help_url = self.__di.settings_controller.create_help_link()
                self.__di.telegram_bot_sdk.send_button_link(self.__di.invoker.telegram_chat_id, help_url)
                self.sprint("Shared the help link with the user")
                return CommandProcessor.Result.success

            raise ValueError(f"Unknown command '{command_name}'")
        except Exception as e:
            self.sprint("Failed to process the command", e)
            return CommandProcessor.Result.failed
