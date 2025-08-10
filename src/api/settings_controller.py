from dataclasses import asdict
from typing import Annotated, Any, List, Literal, TypeAlias, get_args

from api import auth
from api.mapper.chat_mapper import domain_to_api as chat_to_api
from api.mapper.user_mapper import api_to_domain, domain_to_api
from api.model.chat_settings_payload import ChatSettingsPayload
from api.model.external_tools_response import ExternalToolProviderResponse, ExternalToolResponse, ExternalToolsResponse
from api.model.user_settings_payload import UserSettingsPayload
from db.model.chat_config import ChatConfigDB
from db.schema.chat_config import ChatConfig, ChatConfigSave
from db.schema.sponsorship import Sponsorship
from db.schema.user import User
from di.di import DI
from features.external_tools.external_tool_library import ALL_EXTERNAL_TOOLS
from features.external_tools.external_tool_provider_library import ALL_PROVIDERS
from util import log
from util.config import config

SettingsType: TypeAlias = Annotated[str, Literal["user", "chat"]]
InvokerType: TypeAlias = Annotated[str, Literal["creator", "administrator"]]
DEF_SETTINGS_TYPE: SettingsType = "user"
SETTINGS_TOKEN_VAR: str = "token"


class SettingsController:

    __di: DI

    def __init__(self, di: DI):
        self.__di = di

    def __validate_settings_type(self, settings_type: str) -> SettingsType:
        log.d("Validating settings type")
        literal_type = get_args(SettingsType)[1]
        if settings_type not in get_args(literal_type):
            raise ValueError(log.e(f"Invalid settings type '{settings_type}'"))
        return settings_type

    def create_settings_link(self, raw_settings_type: str | None = None) -> str:
        if not self.__di.invoker.telegram_chat_id:
            raise ValueError(log.e("User never sent a private message, cannot create a settings link"))

        settings_type = self.__validate_settings_type(raw_settings_type) if raw_settings_type else DEF_SETTINGS_TYPE
        chat_config = self.__di.authorization_service.authorize_for_chat(self.__di.invoker, self.__di.invoker_chat)
        resource_id: str = self.__di.invoker.id.hex if settings_type == "user" else chat_config.chat_id.hex
        lang_iso_code: str = chat_config.language_iso_code or "en"

        sponsored_by = self.__resolve_sponsor_name()
        jwt_token = self.__create_jwt_token(sponsored_by)

        page = "sponsorships" if (settings_type == "user" and sponsored_by) else "settings"
        settings_url_base = f"{config.backoffice_url_base}/{lang_iso_code}/{settings_type}/{resource_id}/{page}"
        return f"{settings_url_base}?{SETTINGS_TOKEN_VAR}={jwt_token}"

    def create_help_link(self) -> str:
        lang_iso_code: str = "en"
        if not self.__di.invoker.telegram_chat_id:
            raise ValueError(log.e("User never sent a private message, cannot create settings link"))
        chat_config = self.__di.authorization_service.authorize_for_chat(self.__di.invoker, self.__di.invoker_chat)
        if chat_config.language_iso_code:
            lang_iso_code = chat_config.language_iso_code

        jwt_token = self.__create_jwt_token()
        settings_url_base = f"{config.backoffice_url_base}/{lang_iso_code}/features"
        return f"{settings_url_base}?{SETTINGS_TOKEN_VAR}={jwt_token}"

    def fetch_external_tools(self, user_id_hex: str) -> dict[str, Any]:
        user = self.__di.authorization_service.authorize_for_user(self.__di.invoker, user_id_hex)
        scoped_di = self.__di.clone(invoker_id = user.id.hex)
        tools: List[ExternalToolResponse] = []
        providers: List[ExternalToolProviderResponse] = []
        for tool in ALL_EXTERNAL_TOOLS:
            is_configured = scoped_di.access_token_resolver.get_access_token_for_tool(tool) is not None
            tools.append(ExternalToolResponse(tool, is_configured))
        for provider in ALL_PROVIDERS:
            is_configured = scoped_di.access_token_resolver.get_access_token(provider) is not None
            providers.append(ExternalToolProviderResponse(provider, is_configured))
        return asdict(ExternalToolsResponse(tools, providers))

    def fetch_chat_settings(self, chat_id: str) -> dict[str, Any]:
        chat_config = self.__di.authorization_service.authorize_for_chat(self.__di.invoker, chat_id)
        invoker_telegram_id = str(self.__di.invoker.telegram_user_id or 0)
        return chat_to_api(chat = chat_config, is_own = invoker_telegram_id == chat_config.external_id).model_dump()

    def fetch_user_settings(self, user_id_hex: str) -> dict[str, Any]:
        user = self.__di.authorization_service.authorize_for_user(self.__di.invoker, user_id_hex)
        return domain_to_api(user).model_dump()

    def save_chat_settings(self, chat_id: str, payload: ChatSettingsPayload):
        log.d(f"Saving chat settings for chat '{chat_id}'")
        chat_config = self.__di.authorization_service.authorize_for_chat(self.__di.invoker, chat_id)
        chat_config_save = ChatConfigSave(**chat_config.model_dump())

        # validate language changes
        if not payload.language_name or not payload.language_iso_code:
            raise ValueError(log.e("Both language_name and language_iso_code must be non-empty"))
        log.t(f"  Updating language to '{payload.language_name}' ({payload.language_iso_code})")
        chat_config_save.language_name = payload.language_name
        chat_config_save.language_iso_code = payload.language_iso_code

        # validate reply chance changes
        if chat_config_save.is_private and payload.reply_chance_percent != 100:
            raise ValueError(log.e("Chat is private, reply chance cannot be changed"))
        log.t(f"  Updating reply chance to {payload.reply_chance_percent}%")
        chat_config_save.reply_chance_percent = payload.reply_chance_percent

        # validate release notifications changes
        release_notifications = ChatConfigDB.ReleaseNotifications.lookup(payload.release_notifications)
        if not release_notifications:
            raise ValueError(log.e(f"Invalid release notifications setting value '{payload.release_notifications}'"))
        log.t(f"  Updating release notifications to '{release_notifications.value}'")
        chat_config_save.release_notifications = release_notifications

        # finally store the changes
        ChatConfig.model_validate(self.__di.chat_config_crud.save(chat_config_save))
        log.i("Chat settings saved")

    def save_user_settings(self, user_id_hex: str, payload: UserSettingsPayload):
        log.d(f"Saving user settings for user '{user_id_hex}'")
        user = self.__di.authorization_service.authorize_for_user(self.__di.invoker, user_id_hex)

        # validate tool choices
        configured_tools = self.fetch_external_tools(user_id_hex)
        configured_tool_ids = {tool["definition"]["id"] for tool in configured_tools["tools"] if tool["is_configured"]}
        for key, value in payload.model_dump().items():
            if key.startswith("tool_choice_") and value and (value not in configured_tool_ids):
                raise ValueError(log.e(f"Invalid tool choice '{value}' for '{key}'. Tool is not configured."))

        user_save = api_to_domain(payload, user)
        User.model_validate(self.__di.user_crud.save(user_save))
        log.i("User settings saved")

    def fetch_admin_chats(self, user_id_hex: str) -> list[dict[str, Any]]:
        log.d("Fetching administered chats")
        user = self.__di.authorization_service.authorize_for_user(self.__di.invoker, user_id_hex)
        admin_chats = self.__di.authorization_service.get_authorized_chats(user)
        result: list[dict[str, Any]] = []
        if not admin_chats:
            log.d("  No administered chats found")
            return result
        owner_telegram_chat_id = str(user.telegram_chat_id or 0)
        for chat_config in admin_chats:
            record = {
                "chat_id": chat_config.chat_id.hex,
                "title": chat_config.title,
                "is_own": owner_telegram_chat_id == chat_config.external_id,
            }
            result.append(record)
        return result

    def __resolve_sponsor_name(self) -> str | None:
        sponsored_by: str | None = None
        sponsorships_db = self.__di.sponsorship_crud.get_all_by_receiver(self.__di.invoker.id)
        if sponsorships_db:
            sponsorship = Sponsorship.model_validate(sponsorships_db[0])
            sponsor_db = self.__di.user_crud.get(sponsorship.sponsor_id)
            if sponsor_db:
                sponsor = User.model_validate(sponsor_db)
                sponsored_by = sponsor.full_name or sponsor.telegram_username  # or None, transitively
        return sponsored_by

    def __create_jwt_token(self, sponsored_by: str | None = None) -> str:
        sponsored_by = sponsored_by or self.__resolve_sponsor_name()
        telegram_user_id = self.__di.invoker.telegram_user_id
        telegram_username = self.__di.invoker.telegram_username
        token_payload = {
            "iss": config.telegram_bot_name,  # issuer, app name
            "sub": self.__di.invoker.id.hex,  # subject, user's unique identifier
            **({"telegram_user_id": telegram_user_id} if telegram_user_id else {}),
            **({"telegram_username": telegram_username} if telegram_username else {}),
            **({"sponsored_by": sponsored_by} if sponsored_by else {}),
        }
        return auth.create_jwt_token(token_payload, config.jwt_expires_in_minutes)
