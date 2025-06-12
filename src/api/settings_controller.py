from typing import Literal, Any, TypeAlias, Annotated, get_args

from api.auth import create_jwt_token
from api.authorization_service import AuthorizationService
from db.crud.chat_config import ChatConfigCRUD
from db.crud.user import UserCRUD
from db.schema.chat_config import ChatConfig
from db.schema.user import User, UserSave
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

    __authorization_service: AuthorizationService
    __chat_config_manager: ChatConfigManager
    __user_dao: UserCRUD

    def __init__(
        self,
        invoker_user_id_hex: str,
        telegram_sdk: TelegramBotSDK,
        user_dao: UserCRUD,
        chat_config_dao: ChatConfigCRUD,
    ):
        super().__init__(config.verbose)
        self.__authorization_service = AuthorizationService(telegram_sdk, user_dao, chat_config_dao)
        self.__chat_config_manager = ChatConfigManager(chat_config_dao)
        self.__user_dao = user_dao
        self.invoker_user = self.__authorization_service.validate_user(invoker_user_id_hex)

    def __validate_settings_type(self, settings_type: str) -> SettingsType:
        self.sprint("Validating settings type")
        literal_type = get_args(SettingsType)[1]
        if settings_type not in get_args(literal_type):
            message = f"Invalid settings type '{settings_type}'"
            self.sprint(message)
            raise ValueError(message)
        return settings_type

    def create_settings_link(self, raw_settings_type: str | None = None, target_chat_id: str | None = None) -> str:
        resource_id: str
        lang_iso_code: str = "en"
        settings_type = self.__validate_settings_type(raw_settings_type) if raw_settings_type else DEF_SETTINGS_TYPE
        if settings_type == "user":
            user_chat_id: str | None = self.invoker_user.telegram_chat_id
            chat_config: ChatConfig | None = None
            if user_chat_id:
                try:
                    chat_config = self.__authorization_service.authorize_for_chat(self.invoker_user, user_chat_id)
                except ValueError:
                    # User doesn't have access to their own chat (shouldn't happen normally)
                    chat_config = None
            if chat_config and chat_config.language_iso_code:
                lang_iso_code = chat_config.language_iso_code
            resource_id = self.invoker_user.id.hex
        elif settings_type == "chat":
            if not target_chat_id:
                message = "Chat ID must be provided when requesting chat settings"
                self.sprint(message)
                raise ValueError(message)
            authorized_chat_config: ChatConfig = self.__authorization_service.authorize_for_chat(
                self.invoker_user, target_chat_id
            )
            lang_iso_code = authorized_chat_config.language_iso_code or "en"
            resource_id = authorized_chat_config.chat_id
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

    def fetch_chat_settings(self, chat_id: str) -> dict[str, Any]:
        chat_config = self.__authorization_service.authorize_for_chat(self.invoker_user, chat_id)
        output = ChatConfig.model_dump(chat_config)
        invoker_telegram_id = str(self.invoker_user.telegram_user_id or 0)
        output["is_own"] = invoker_telegram_id == chat_config.chat_id
        return output

    def fetch_user_settings(self, user_id_hex: str) -> dict[str, Any]:
        user = self.__authorization_service.authorize_for_user(self.invoker_user, user_id_hex)
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
        chat_config = self.__authorization_service.authorize_for_chat(self.invoker_user, chat_id)
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
        user = self.__authorization_service.authorize_for_user(self.invoker_user, user_id_hex)
        user.open_ai_key = open_ai_key
        user_db = self.__user_dao.save(UserSave(**user.model_dump()))
        User.model_validate(user_db)
        self.sprint("  User settings saved")

    def fetch_admin_chats(self, user_id_hex: str) -> list[dict[str, Any]]:
        self.sprint("Fetching administered chats")
        user = self.__authorization_service.authorize_for_user(self.invoker_user, user_id_hex)
        admin_chats = self.__authorization_service.get_authorized_chats(user)
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
