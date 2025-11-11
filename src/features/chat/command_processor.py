from enum import Enum

from di.di import DI
from features.integrations.integrations import resolve_agent_user, resolve_external_handle, resolve_private_chat_id
from util import log

COMMAND_START = "start"
COMMAND_SETTINGS = "settings"
COMMAND_HELP = "help"
COMMAND_CONNECT = "connect"
SUPPORTED_COMMANDS = [COMMAND_START, COMMAND_SETTINGS, COMMAND_HELP, COMMAND_CONNECT]


class CommandProcessor:

    class Result(Enum):
        failed = "Failed"
        unknown = "Unknown"
        success = "Success"

    __di: DI

    def __init__(self, di: DI):
        self.__di = di

    def execute(self, raw_input: str) -> Result:
        log.t(f"Starting to evaluate command input '{raw_input}'")
        try:
            if not raw_input:
                log.w("Nothing to process")
                return CommandProcessor.Result.unknown
            command_parts = raw_input.split()
            if command_parts and command_parts[0].startswith("/"):
                # bot is sometimes tagged like this: /start@my_bot
                full_command_with_tag = command_parts[0]  # discard command arguments
                core_command: str
                if "@" in full_command_with_tag:
                    chat_type = self.__di.require_invoker_chat_type()
                    core_command, bot_tag = full_command_with_tag.split("@")
                    agent_user = resolve_agent_user(chat_type)
                    agent_handle = resolve_external_handle(agent_user, chat_type)
                    if bot_tag != agent_handle:
                        log.d(f"Unknown bot tagged: '{bot_tag}'")
                        return CommandProcessor.Result.unknown
                else:
                    core_command = full_command_with_tag
                command_name = core_command[1:]
                command_args = command_parts[1:]
                if command_name in SUPPORTED_COMMANDS:
                    return self.__handle_config_commands(command_name, command_args)
            log.t("No known command found")
            return CommandProcessor.Result.unknown
        except Exception as e:
            log.e("Failed to process command", e)
            return CommandProcessor.Result.failed

    def __handle_config_commands(self, command_name: str, command_args: list[str]) -> Result:
        log.t(f"Processing the config command '{command_name}' and args '{command_args}'")
        try:
            platform_private_chat_id = resolve_private_chat_id(self.__di.invoker, self.__di.require_invoker_chat_type()) or "-1"

            if command_name in [COMMAND_START, COMMAND_SETTINGS]:
                # try to accept a sponsorship (works if this is the first message and user is pre-sponsored)
                if command_name == COMMAND_START:
                    if self.__di.sponsorship_service.accept_sponsorship(self.__di.invoker):
                        log.d("Accepted a sponsorship by messaging the bot")
                        return CommandProcessor.Result.success
                # no sponsorship accepted, so let's share the settings link
                settings_url = self.__di.settings_controller.create_settings_link().settings_link
                self.__di.platform_bot_sdk().send_button_link(platform_private_chat_id, settings_url)
                log.t("Shared the settings link with the user")
                return CommandProcessor.Result.success

            if command_name == COMMAND_HELP:
                # share the help link
                help_url = self.__di.settings_controller.create_help_link()
                self.__di.platform_bot_sdk().send_button_link(platform_private_chat_id, help_url)
                log.t("Shared the help link with the user")
                return CommandProcessor.Result.success

            if command_name == COMMAND_CONNECT:
                # handle profile connection
                if not command_args:
                    # no connect key provided, send settings link
                    settings_url = self.__di.settings_controller.create_settings_link().settings_link
                    self.__di.platform_bot_sdk().send_button_link(platform_private_chat_id, settings_url)
                    log.d("Shared the settings link with the user (no connect key provided)")
                    return CommandProcessor.Result.success

                # try to connect profiles
                connect_key = command_args[0].strip().upper()
                result, message = self.__di.profile_connect_service.connect_profiles(self.__di.invoker, connect_key)
                if result == self.__di.profile_connect_service.Result.success:
                    self.__di.platform_bot_sdk().send_text_message(platform_private_chat_id, "✅")
                    log.t("Profile connection successful")
                    return CommandProcessor.Result.success
                else:
                    # invalid key, send settings link
                    log.w(f"Failed to connect profiles: {message}")
                    settings_url = self.__di.settings_controller.create_settings_link().settings_link
                    self.__di.platform_bot_sdk().send_text_message(platform_private_chat_id, message)
                    self.__di.platform_bot_sdk().send_button_link(platform_private_chat_id, settings_url)
                    log.t("Shared the settings link with the user (invalid connect key)")
                    return CommandProcessor.Result.success

            raise ValueError(f"Unknown command '{command_name}'")
        except Exception as e:
            log.e("Failed to process the command", e)
            return CommandProcessor.Result.failed
