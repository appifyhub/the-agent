from dataclasses import asdict
from typing import Annotated, Any, List, Literal, TypeAlias, get_args

from api.auth import create_jwt_token
from api.authorization_service import AuthorizationService
from api.mapper.user_mapper import api_to_domain, domain_to_api
from api.model.chat_settings_payload import ChatSettingsPayload
from api.model.external_tools_response import ExternalToolProviderResponse, ExternalToolResponse, ExternalToolsResponse
from api.model.user_settings_payload import UserSettingsPayload
from db.crud.chat_config import ChatConfigCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.model.chat_config import ChatConfigDB
from db.schema.chat_config import ChatConfig, ChatConfigSave
from db.schema.sponsorship import Sponsorship
from db.schema.user import User
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.external_tools.access_token_resolver import AccessTokenResolver
from features.external_tools.external_tool_library import ALL_EXTERNAL_TOOLS
from features.external_tools.external_tool_provider_library import ALL_PROVIDERS
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

SettingsType: TypeAlias = Annotated[str, Literal["user", "chat"]]
InvokerType: TypeAlias = Annotated[str, Literal["creator", "administrator"]]
DEF_SETTINGS_TYPE: SettingsType = "user"
SETTINGS_TOKEN_VAR: str = "token"


class SettingsController(SafePrinterMixin):
    __invoker_user: User
    __authorization_service: AuthorizationService
    __chat_config_dao: ChatConfigCRUD
    __user_dao: UserCRUD
    __sponsorship_dao: SponsorshipCRUD

    def __init__(
        self,
        invoker_user_id_hex: str,
        telegram_sdk: TelegramBotSDK,
        user_dao: UserCRUD,
        chat_config_dao: ChatConfigCRUD,
        sponsorship_dao: SponsorshipCRUD,
    ):
        super().__init__(config.verbose)
        self.__chat_config_dao = chat_config_dao
        self.__user_dao = user_dao
        self.__sponsorship_dao = sponsorship_dao
        self.__authorization_service = AuthorizationService(telegram_sdk, user_dao, chat_config_dao)
        self.__invoker_user = self.__authorization_service.validate_user(invoker_user_id_hex)

    def get_invoker_private_chat_id(self) -> str | None:
        return self.__invoker_user.telegram_chat_id

    def create_settings_link(self, raw_settings_type: str | None = None, target_chat_id: str | None = None) -> str:
        resource_id: str
        chat_config: ChatConfig
        lang_iso_code: str = "en"
        settings_type = self.__validate_settings_type(raw_settings_type) if raw_settings_type else DEF_SETTINGS_TYPE

        if settings_type == "user":
            resource_id = self.__invoker_user.id.hex
            user_chat_id: str | None = self.__invoker_user.telegram_chat_id
            if not user_chat_id:
                message = "User never sent a private message, cannot create settings link"
                self.sprint(message)
                raise ValueError(message)
            chat_config = self.__authorization_service.authorize_for_chat(self.__invoker_user, user_chat_id)
        elif settings_type == "chat":
            if not target_chat_id:
                message = "Chat ID must be provided when requesting chat settings"
                self.sprint(message)
                raise ValueError(message)
            chat_config = self.__authorization_service.authorize_for_chat(self.__invoker_user, target_chat_id)
            resource_id = chat_config.chat_id
        else:  # should never happen due to validation, let's explode if it does
            message = f"Invalid settings type '{settings_type}'"
            self.sprint(message)
            raise ValueError(message)

        if chat_config.language_iso_code:
            lang_iso_code = chat_config.language_iso_code

        # find the sponsorship information, if available
        sponsored_by: str | None = None
        sponsorships_db = self.__sponsorship_dao.get_all_by_receiver(self.__invoker_user.id)
        if sponsorships_db:
            sponsorship = Sponsorship.model_validate(sponsorships_db[0])
            sponsor_db = self.__user_dao.get(sponsorship.sponsor_id)
            if sponsor_db:
                sponsor = User.model_validate(sponsor_db)
                sponsored_by = sponsor.full_name or sponsor.telegram_username  # or None, transitively

        token_payload = {
            "iss": config.telegram_bot_name,  # issuer, app name
            "sub": self.__invoker_user.id.hex,  # subject, user's unique identifier
            "telegram_user_id": self.__invoker_user.telegram_user_id or -1,
            "telegram_username": self.__invoker_user.telegram_username or "<?>",
        }
        if sponsored_by:
            token_payload["sponsored_by"] = sponsored_by
        page = "sponsorships" if (settings_type == "user" and sponsored_by) else "settings"
        jwt_token = create_jwt_token(token_payload, config.jwt_expires_in_minutes)
        settings_url_base = f"{config.backoffice_url_base}/{lang_iso_code}/{settings_type}/{resource_id}/{page}"
        return f"{settings_url_base}?{SETTINGS_TOKEN_VAR}={jwt_token}"

    def fetch_external_tools(self, user_id_hex: str) -> dict[str, Any]:
        user = self.__authorization_service.authorize_for_user(self.__invoker_user, user_id_hex)
        resolver = AccessTokenResolver(user, self.__user_dao, self.__sponsorship_dao)
        tools: List[ExternalToolResponse] = []
        providers: List[ExternalToolProviderResponse] = []
        for tool in ALL_EXTERNAL_TOOLS:
            is_configured = resolver.get_access_token_for_tool(tool) is not None
            tools.append(ExternalToolResponse(tool, is_configured))
        for provider in ALL_PROVIDERS:
            is_configured = resolver.get_access_token(provider) is not None
            providers.append(ExternalToolProviderResponse(provider, is_configured))
        return asdict(ExternalToolsResponse(tools, providers))

    def fetch_chat_settings(self, chat_id: str) -> dict[str, Any]:
        chat_config = self.__authorization_service.authorize_for_chat(self.__invoker_user, chat_id)
        output = ChatConfig.model_dump(chat_config)
        invoker_telegram_id = str(self.__invoker_user.telegram_user_id or 0)
        output["is_own"] = invoker_telegram_id == chat_config.chat_id
        return output

    def fetch_user_settings(self, user_id_hex: str) -> dict[str, Any]:
        user = self.__authorization_service.authorize_for_user(self.__invoker_user, user_id_hex)
        return domain_to_api(user).model_dump()

    def save_chat_settings(self, chat_id: str, payload: ChatSettingsPayload):
        self.sprint(f"Saving chat settings for chat '{chat_id}'")
        chat_config = self.__authorization_service.authorize_for_chat(self.__invoker_user, chat_id)
        chat_config_save = ChatConfigSave(**chat_config.model_dump())

        # validate language changes
        if not payload.language_name or not payload.language_iso_code:
            message = "Both language_name and language_iso_code must be non-empty"
            self.sprint(message)
            raise ValueError(message)
        self.sprint(f"  Updating language to '{payload.language_name}' ({payload.language_iso_code})")
        chat_config_save.language_name = payload.language_name
        chat_config_save.language_iso_code = payload.language_iso_code

        # validate reply chance changes
        if chat_config_save.is_private and payload.reply_chance_percent != 100:
            message = "Chat is private, reply chance cannot be changed"
            self.sprint(message)
            raise ValueError(message)
        self.sprint(f"  Updating reply chance to {payload.reply_chance_percent}%")
        chat_config_save.reply_chance_percent = payload.reply_chance_percent

        # validate release notifications changes
        release_notifications = ChatConfigDB.ReleaseNotifications.lookup(payload.release_notifications)
        if not release_notifications:
            message = f"Invalid release notifications setting value '{payload.release_notifications}'"
            self.sprint(message)
            raise ValueError(message)
        self.sprint(f"  Updating release notifications to '{release_notifications.value}'")
        chat_config_save.release_notifications = release_notifications

        # finally store the changes
        ChatConfig.model_validate(self.__chat_config_dao.save(chat_config_save))
        self.sprint("Chat settings saved")

    def save_user_settings(self, user_id_hex: str, payload: UserSettingsPayload):
        self.sprint(f"Saving user settings for user '{user_id_hex}'")
        user = self.__authorization_service.authorize_for_user(self.__invoker_user, user_id_hex)
        user_save = api_to_domain(payload, user)
        User.model_validate(self.__user_dao.save(user_save))
        self.sprint("User settings saved")

    def fetch_admin_chats(self, user_id_hex: str) -> list[dict[str, Any]]:
        self.sprint("Fetching administered chats")
        user = self.__authorization_service.authorize_for_user(self.__invoker_user, user_id_hex)
        admin_chats = self.__authorization_service.get_authorized_chats(user)
        result: list[dict[str, Any]] = []
        if not admin_chats:
            self.sprint("  No administered chats found")
            return result
        invoker_telegram_chat_id = str(self.__invoker_user.telegram_chat_id or 0)
        for chat_config in admin_chats:
            record = {
                "chat_id": chat_config.chat_id,
                "title": chat_config.title,
                "is_own": invoker_telegram_chat_id == chat_config.chat_id,
            }
            result.append(record)
        return result

    def __validate_settings_type(self, settings_type: str) -> SettingsType:
        self.sprint("Validating settings type")
        literal_type = get_args(SettingsType)[1]
        if settings_type not in get_args(literal_type):
            message = f"Invalid settings type '{settings_type}'"
            self.sprint(message)
            raise ValueError(message)
        return settings_type
