from typing import Literal, Dict, Any
from uuid import UUID

from db.crud.chat_config import ChatConfigCRUD
from db.crud.user import UserCRUD
from db.schema.chat_config import ChatConfig
from db.schema.user import User
from features.auth import create_jwt_token
from features.chat.telegram.model.chat_member import ChatMemberOwner, ChatMemberAdministrator
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from util.config import config
from util.functions import mask_secret
from util.safe_printer_mixin import SafePrinterMixin, sprint


class SettingsManager(SafePrinterMixin):
    __invoker_user: User
    __chat_config: ChatConfig
    __invoker_status: Literal["creator", "administrator"]
    __settings_type: Literal["user_settings", "chat_settings"] | None

    __telegram_sdk: TelegramBotSDK
    __user_dao: UserCRUD
    __chat_config_dao: ChatConfigCRUD

    @staticmethod
    def resolve_user_id_hex_and_chat_id(token_claims: Dict[str, Any]) -> tuple[str, str]:
        if not token_claims:
            message = "Empty token"
            sprint(message)
            raise ValueError(message)
        user_id_hex = token_claims.get("sub")
        chat_id = token_claims.get("chat_id")
        if not user_id_hex or not chat_id:
            message = "Invalid token, 'sub' or 'chat_id' not found"
            sprint(message)
            raise ValueError(message)
        return user_id_hex, chat_id

    def __init__(
        self,
        invoker_user_id_hex: str,
        target_chat_id: str,
        telegram_sdk: TelegramBotSDK,
        user_dao: UserCRUD,
        chat_config_dao: ChatConfigCRUD,
        settings_type: str | None = None,
    ):
        super().__init__(config.verbose)
        self.__telegram_sdk = telegram_sdk
        self.__user_dao = user_dao
        self.__chat_config_dao = chat_config_dao
        self.__validate(invoker_user_id_hex, target_chat_id, settings_type)

    def __validate(self, invoker_user_id_hex: str, target_chat_id: str, settings_type: str | None):
        self.sprint("Validating settings type")
        if settings_type and settings_type not in ["user_settings", "chat_settings"]:
            message = f"Invalid settings type '{settings_type}'"
            self.sprint(message)
            raise ValueError(message)
        self.__settings_type = settings_type

        self.sprint("Validating settings invoker data")
        invoker_user_db = self.__user_dao.get(UUID(hex = invoker_user_id_hex))
        if not invoker_user_db:
            message = f"Invoker '{invoker_user_id_hex}' not found"
            self.sprint(message)
            raise ValueError(message)
        self.__invoker_user = User.model_validate(invoker_user_db)

        self.sprint("Validating settings target chat data")
        chat_config_db = self.__chat_config_dao.get(target_chat_id)
        if not chat_config_db:
            message = f"Chat '{target_chat_id}' not found"
            self.sprint(message)
            raise ValueError(message)
        self.__chat_config = ChatConfig.model_validate(chat_config_db)

        self.sprint("Validating admin rights for invoker")
        invoker_as_member = self.__telegram_sdk.get_chat_member(
            self.__chat_config.chat_id,
            self.__invoker_user.telegram_user_id,
        )
        is_private = self.__chat_config.is_private and \
                     self.__chat_config.chat_id == str(self.__invoker_user.telegram_user_id)
        if not is_private and \
            not isinstance(invoker_as_member, ChatMemberOwner) and \
            not isinstance(invoker_as_member, ChatMemberAdministrator):
            message = f"User @{self.__invoker_user.telegram_username} is not an admin in '{self.__chat_config.title}'"
            self.sprint(message)
            raise ValueError(message)
        self.__invoker_status = "creator" if is_private else invoker_as_member.status

    def create_settings_link(self) -> str:
        settings_type = self.__settings_type or "chat_settings"  # it's safer for group chats to default to chat settings
        lang_iso_code: str = self.__chat_config.language_iso_code or "en"
        resource_id = self.__invoker_user.id.hex if settings_type == "user_settings" else self.__chat_config.chat_id
        resource_type = "user" if settings_type == "user_settings" else "chat"
        token_payload = {
            "iss": config.telegram_bot_name,  # issuer, app name
            "sub": self.__invoker_user.id.hex,  # subject, unique identifier
            "aud": self.__chat_config.title,  # audience, chat title
            "role": self.__invoker_status,  # role, admin status
            "chat_id": self.__chat_config.chat_id,
            "telegram_user_id": self.__invoker_user.telegram_user_id,
            "telegram_username": self.__invoker_user.telegram_username,
        }
        jwt_token = create_jwt_token(token_payload)
        return f"{config.backoffice_url_base}/{lang_iso_code}/{resource_type}/{resource_id}/settings?token={jwt_token}"

    def send_settings_link(self, link_url: str) -> None:
        url_type = self.__settings_type or "chat_settings"
        # noinspection PyTypeChecker
        self.__telegram_sdk.send_button_link(
            chat_id = self.__invoker_user.telegram_user_id,  # always send to private chat
            link_url = link_url,
            url_type = url_type,
        )
        self.sprint(f"Sent the button link to private chat '{self.__invoker_user.telegram_user_id}'")

    def authorize_for_chat(self, chat_id: str) -> ChatConfig:
        chat_config_db = self.__chat_config_dao.get(chat_id)
        if not chat_config_db:
            message = f"Chat '{chat_id}' not found"
            self.sprint(message)
            raise ValueError(message)
        chat_config = ChatConfig.model_validate(chat_config_db)
        if self.__chat_config.chat_id != chat_config.chat_id:
            message = f"Target chat '{chat_id}' is not the allowed chat '{self.__chat_config.chat_id}'"
            self.sprint(message)
            raise ValueError(message)
        return chat_config

    def authorize_for_user(self, user_id_hex: str) -> User:
        user_db = self.__user_dao.get(UUID(hex = user_id_hex))
        if not user_db:
            message = f"User '{user_id_hex}' not found"
            self.sprint(message)
            raise ValueError(message)
        user = User.model_validate(user_db)
        if self.__invoker_user.id != user.id:
            message = f"Target user '{user_id_hex}' is not the allowed user '{self.__invoker_user.id.hex}'"
            self.sprint(message)
            raise ValueError(message)
        return user

    def fetch_chat_settings(self, chat_id: str) -> dict[str, Any]:
        chat_config = self.authorize_for_chat(chat_id)
        output = ChatConfig.model_dump(chat_config)
        output["is_own"] = str(self.__invoker_user.telegram_user_id or 0) == chat_config.chat_id
        return output

    def fetch_user_settings(self, user_id_hex: str) -> dict[str, Any]:
        user = self.authorize_for_user(user_id_hex)
        output = User.model_dump(user)
        output["id"] = user.id.hex
        output["open_ai_key"] = mask_secret(output["open_ai_key"])
        return output
