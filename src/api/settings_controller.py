from typing import Literal, Any, TypeAlias, Annotated, get_args
from uuid import UUID

from db.crud.chat_config import ChatConfigCRUD
from db.crud.user import UserCRUD
from db.schema.chat_config import ChatConfig
from db.schema.user import User, UserSave
from api.auth import create_jwt_token
from features.chat.chat_config_manager import ChatConfigManager
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from util.config import config
from util.functions import mask_secret
from util.safe_printer_mixin import SafePrinterMixin

SettingsType: TypeAlias = Annotated[str, Literal["user", "chat"]]
InvokerType: TypeAlias = Annotated[str, Literal["creator", "administrator"]]
DEF_SETTINGS_TYPE: SettingsType = "user"
SETTINGS_TOKEN_VAR: str = "token"


class SettingsController(SafePrinterMixin):
    invoker_user: User

    __telegram_sdk: TelegramBotSDK
    __chat_config_manager: ChatConfigManager
    __user_dao: UserCRUD
    __chat_config_dao: ChatConfigCRUD

    def __init__(
        self,
        invoker_user_id_hex: str,
        telegram_sdk: TelegramBotSDK,
        user_dao: UserCRUD,
        chat_config_dao: ChatConfigCRUD,
    ):
        super().__init__(config.verbose)
        self.__telegram_sdk = telegram_sdk
        self.__user_dao = user_dao
        self.__chat_config_dao = chat_config_dao
        self.__chat_config_manager = ChatConfigManager(chat_config_dao)
        self.__validate_invoker(invoker_user_id_hex)

    def __validate_invoker(self, invoker_user_id_hex: str) -> User:
        self.sprint("Validating invoker data")
        invoker_user_db = self.__user_dao.get(UUID(hex = invoker_user_id_hex))
        if not invoker_user_db:
            message = f"Invoker '{invoker_user_id_hex}' not found"
            self.sprint(message)
            raise ValueError(message)
        self.invoker_user = User.model_validate(invoker_user_db)
        return self.invoker_user

    def __validate_chat(self, chat_id: str) -> ChatConfig:
        self.sprint("Validating chat data")
        chat_config_db = self.__chat_config_dao.get(chat_id)
        if not chat_config_db:
            message = f"Chat '{chat_id}' not found"
            self.sprint(message)
            raise ValueError(message)
        return ChatConfig.model_validate(chat_config_db)

    def __validate_settings_type(self, settings_type: str) -> SettingsType:
        self.sprint("Validating settings type")
        literal_type = get_args(SettingsType)[1]
        if settings_type not in get_args(literal_type):
            message = f"Invalid settings type '{settings_type}'"
            self.sprint(message)
            raise ValueError(message)
        return settings_type

    def create_settings_link(self, raw_settings_type: str | None = None, chat_id: str | None = None) -> str:
        resource_id: str
        lang_iso_code: str = "en"
        settings_type = self.__validate_settings_type(raw_settings_type) if raw_settings_type else DEF_SETTINGS_TYPE
        if settings_type == "user":
            chat_id: str | None = self.invoker_user.telegram_chat_id
            chat_config: ChatConfig | None = self.authorize_for_chat(chat_id) if chat_id else None
            if chat_config and chat_config.language_iso_code:
                lang_iso_code = chat_config.language_iso_code
            resource_id = self.invoker_user.id.hex
        elif settings_type == "chat":
            if not chat_id:
                message = "Chat ID must be provided when requesting chat settings"
                self.sprint(message)
                raise ValueError(message)
            chat_config: ChatConfig = self.authorize_for_chat(chat_id)
            lang_iso_code: str = chat_config.language_iso_code or "en"
            resource_id = chat_config.chat_id
        else:
            # should never happen due to validation, let's explode if it does
            message = f"Invalid settings type '{settings_type}'"
            self.sprint(message)
            raise ValueError(message)
        token_payload = {
            "iss": config.telegram_bot_name,  # issuer, app name
            "sub": self.invoker_user.id.hex,  # subject, user's unique identifier
            "telegram_user_id": self.invoker_user.telegram_user_id,
            "telegram_username": self.invoker_user.telegram_username,
        }
        jwt_token = create_jwt_token(token_payload, config.jwt_expires_in_minutes)
        settings_url_base = f"{config.backoffice_url_base}/{lang_iso_code}/{settings_type}/{resource_id}/settings"
        return f"{settings_url_base}?{SETTINGS_TOKEN_VAR}={jwt_token}"

    def get_admin_chats_for_user(self, user: User) -> list[ChatConfig]:
        self.sprint(f"Getting administered chats for user {user.id.hex}")

        if not user.telegram_user_id:
            self.sprint(f"  User {user.id.hex} has no telegram_user_id")
            return []

        self.sprint("  Validating chat configurations")
        max_chats = config.max_users * 10  # assuming each user administers 10 chats
        all_chat_configs_db = self.__chat_config_dao.get_all(limit = max_chats)
        if not all_chat_configs_db:
            self.sprint("  No chat configurations found in DB")
            return []
        all_chat_configs = [ChatConfig.model_validate(chat_config_db) for chat_config_db in all_chat_configs_db]
        self.sprint(f"  Found {len(all_chat_configs)} chat configurations to check")

        self.sprint("  Checking admin status in each chat")
        administered_chats: list[ChatConfig] = []
        for chat_config in all_chat_configs:
            self.sprint(f"    Checking chat: {chat_config.title} ({chat_config.chat_id})")
            try:
                if chat_config.is_private:
                    if user.telegram_chat_id == chat_config.chat_id:
                        self.sprint(f"    Chat {chat_config.chat_id} is private and matches invoker's chat ID")
                        administered_chats.append(chat_config)
                    else:
                        self.sprint(f"    Chat {chat_config.chat_id} is private but does not match invoker's chat ID")
                    continue

                administrators = self.__telegram_sdk.get_chat_administrators(chat_config.chat_id)
                if not administrators:
                    self.sprint(f"    No administrators returned for chat {chat_config.chat_id}")
                    continue
                for admin_member in administrators:
                    if admin_member.user and admin_member.user.id == user.telegram_user_id:
                        self.sprint(f"    User {admin_member.user.id} IS admin in '{chat_config.chat_id}'")
                        administered_chats.append(chat_config)
                        break
                else:
                    self.sprint(f"    User {user.telegram_user_id} is NOT admin in '{chat_config.chat_id}'")
            except Exception as e:
                self.sprint(f"    Error checking administrators for '{chat_config.chat_id}'", e)

        self.sprint("  Sorting administered chats now")
        administered_chats.sort(
            key = lambda chat: (
                not chat.is_private,
                chat.title.lower() if chat.title else "",
                chat.chat_id,
            )
        )
        return administered_chats

    def authorize_for_chat(self, chat_id: str) -> ChatConfig:
        self.sprint(f"Validating admin rights for invoker in chat '{chat_id}'")
        chat_config = self.__validate_chat(chat_id)
        admin_chat_configs = self.get_admin_chats_for_user(self.invoker_user)
        for admin_chat_config in admin_chat_configs:
            if admin_chat_config.chat_id == chat_config.chat_id:
                return chat_config
        message = f"User '{self.invoker_user.id.hex}' is not admin in '{chat_config.title}'"
        self.sprint(message)
        raise ValueError(message)

    def authorize_for_user(self, user_id_hex: str) -> User:
        user_db = self.__user_dao.get(UUID(hex = user_id_hex))
        if not user_db:
            message = f"User '{user_id_hex}' not found"
            self.sprint(message)
            raise ValueError(message)
        user = User.model_validate(user_db)
        if self.invoker_user.id != user.id:
            message = f"Target user '{user_id_hex}' is not the allowed user '{self.invoker_user.id.hex}'"
            self.sprint(message)
            raise ValueError(message)
        return user

    def fetch_chat_settings(self, chat_id: str) -> dict[str, Any]:
        chat_config = self.authorize_for_chat(chat_id)
        output = ChatConfig.model_dump(chat_config)
        invoker_telegram_id = str(self.invoker_user.telegram_user_id or 0)
        output["is_own"] = invoker_telegram_id == chat_config.chat_id
        return output

    def fetch_user_settings(self, user_id_hex: str) -> dict[str, Any]:
        user = self.authorize_for_user(user_id_hex)
        output = User.model_dump(user)
        output["id"] = user.id.hex
        output["open_ai_key"] = mask_secret(output.get("open_ai_key"))
        return output

    def save_chat_settings(
        self,
        chat_id: str,
        language_name: str,
        language_iso_code: str,
        reply_chance_percent: int,
        release_notifications: str,
    ):
        self.sprint(f"Saving chat settings for chat '{chat_id}'")
        chat_config = self.authorize_for_chat(chat_id)
        result, message = self.__chat_config_manager.change_chat_language(
            chat_id = chat_config.chat_id,
            language_name = language_name,
            language_iso_code = language_iso_code,
        )
        if result == ChatConfigManager.Result.failure:
            raise ValueError(message)
        self.sprint("  Chat language changed")
        result, message = self.__chat_config_manager.change_chat_reply_chance(
            chat_id = chat_config.chat_id,
            reply_chance_percent = reply_chance_percent,
        )
        if result == ChatConfigManager.Result.failure:
            raise ValueError(message)
        self.sprint("  Reply chance changed")
        result, message = self.__chat_config_manager.change_chat_release_notifications(
            chat_id = chat_config.chat_id,
            raw_selection = release_notifications,
        )
        if result == ChatConfigManager.Result.failure:
            raise ValueError(message)
        self.sprint("  Release notifications changed")

    def save_user_settings(self, user_id_hex: str, open_ai_key: str):
        self.sprint(f"Saving user settings for user '{user_id_hex}'")
        user = self.authorize_for_user(user_id_hex)
        user.open_ai_key = open_ai_key
        user_db = self.__user_dao.save(UserSave(**user.model_dump()))
        User.model_validate(user_db)
        self.sprint("  User settings saved")

    def fetch_admin_chats(self, user_id_hex: str) -> list[dict[str, Any]]:
        self.sprint("Fetching administered chats")
        user = self.authorize_for_user(user_id_hex)
        admin_chats = self.get_admin_chats_for_user(user)
        result: list[dict[str, Any]] = []
        if not admin_chats:
            self.sprint("  No administered chats found")
            return result
        invoker_telegram_chat_id = str(self.invoker_user.telegram_chat_id or 0)
        for chat_config in admin_chats:
            record = {
                "chat_id": chat_config.chat_id,
                "title": chat_config.title,
                "is_own": invoker_telegram_chat_id == chat_config.chat_id,
            }
            result.append(record)
        return result
