from contextlib import asynccontextmanager
from typing import Literal, Any

from fastapi import Depends, FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse

from db.crud.chat_config import ChatConfigCRUD
from db.crud.chat_message import ChatMessageCRUD
from db.crud.invite import InviteCRUD
from db.crud.price_alert import PriceAlertCRUD
from db.crud.tools_cache import ToolsCacheCRUD
from db.crud.user import UserCRUD
from db.sql import get_session, initialize_db
from features.auth import verify_api_key, verify_telegram_auth_key, verify_jwt_credentials
from features.chat.invite_manager import InviteManager
from features.chat.settings_manager import SettingsManager
from features.chat.telegram.domain_langchain_mapper import DomainLangchainMapper
from features.chat.telegram.model.update import Update
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.chat.telegram.telegram_data_resolver import TelegramDataResolver
from features.chat.telegram.telegram_domain_mapper import TelegramDomainMapper
from features.chat.telegram.telegram_price_alert_responder import respond_with_announcements
from features.chat.telegram.telegram_summary_responder import respond_with_summary
from features.chat.telegram.telegram_update_responder import respond_to_update
from features.release_summarizer.raw_notes_payload import ReleaseOutputPayload
from util.config import config
from util.safe_printer_mixin import sprint
from util.translations_cache import TranslationsCache


# noinspection PyUnusedLocal
@asynccontextmanager
async def lifespan(owner: FastAPI):
    # startup
    sprint("Lifecycle: Starting up endpoints...")
    initialize_db()
    yield
    # shutdown
    sprint("Lifecycle: Shutting down...")


app = FastAPI(
    docs_url = None,
    redoc_url = None,
    title = "The Agent's API",
    description = "This is the API service for The Agent.",
    debug = config.verbose,
    lifespan = lifespan,
)

# noinspection PyTypeChecker
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = False,
    allow_methods = ["*"],
    allow_headers = ["*"],
)


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url = config.website_url)


@app.get("/health")
def health() -> dict: return {"status": "ok", "version": config.version}


@app.post("/telegram/chat-update")
async def telegram_chat_update(
    update: Update,
    offloader: BackgroundTasks,
    db = Depends(get_session),
    _ = Depends(verify_telegram_auth_key),
) -> dict:
    user_dao = UserCRUD(db)
    invite_dao = InviteCRUD(db)
    telegram_bot_sdk = TelegramBotSDK(db)
    offloader.add_task(
        respond_to_update,
        user_dao = user_dao,
        invite_manager = InviteManager(user_dao, invite_dao),
        chat_message_dao = ChatMessageCRUD(db),
        telegram_domain_mapper = TelegramDomainMapper(),
        telegram_data_resolver = TelegramDataResolver(db, telegram_bot_sdk.api),
        domain_langchain_mapper = DomainLangchainMapper(),
        telegram_bot_sdk = telegram_bot_sdk,
        update = update,
    )
    return {"status": "ok"}


@app.post("/notify/price-alerts")
def notify_of_price_alerts(
    db = Depends(get_session),
    _ = Depends(verify_api_key),
) -> dict:
    return respond_with_announcements(
        user_dao = UserCRUD(db),
        chat_config_dao = ChatConfigCRUD(db),
        price_alert_dao = PriceAlertCRUD(db),
        tools_cache_dao = ToolsCacheCRUD(db),
        telegram_bot_sdk = TelegramBotSDK(db),
        translations = TranslationsCache(),
    )


@app.post("/notify/release")
def notify_of_release(
    payload: ReleaseOutputPayload,
    db = Depends(get_session),
    _ = Depends(verify_api_key),
) -> dict:
    return respond_with_summary(
        chat_config_dao = ChatConfigCRUD(db),
        telegram_bot_sdk = TelegramBotSDK(db),
        translations = TranslationsCache(),
        payload = payload,
    )


@app.post("/task/clear-expired-cache")
def clear_expired_cache(
    db = Depends(get_session),
    _ = Depends(verify_api_key),
) -> dict:
    try:
        cleared_count = ToolsCacheCRUD(db).delete_expired()
        sprint(f"Cleared expired cache entries: {cleared_count}")
        return {"cleared_entries_count": cleared_count}
    except Exception as e:
        sprint("Failed to clear expired cache", e)
        raise HTTPException(status_code = 500, detail = {"reason ": str(e)})


@app.get("/settings/{settings_type}/{resource_id}")
def get_settings(
    settings_type: Literal["user", "chat"],
    resource_id: str,
    db = Depends(get_session),
    token = Depends(verify_jwt_credentials),
) -> dict[str, Any]:
    try:
        sprint(f"Fetching {settings_type} settings for {resource_id}")
        user_id_hex, chat_id = SettingsManager.resolve_user_id_hex_and_chat_id(token)
        sprint(f"  User ID: {user_id_hex}, Chat ID: {chat_id}")
        settings_literal = "user_settings" if settings_type == "user" else "chat_settings"
        user_dao = UserCRUD(db)
        chat_config_dao = ChatConfigCRUD(db)
        settings_manager = SettingsManager(
            invoker_user_id_hex = user_id_hex,
            target_chat_id = chat_id,
            telegram_sdk = TelegramBotSDK(db),
            user_dao = user_dao,
            chat_config_dao = chat_config_dao,
            settings_type = settings_literal,
        )
        if settings_literal == "user_settings":
            return settings_manager.fetch_user_settings(resource_id)
        else:
            return settings_manager.fetch_chat_settings(resource_id)
    except Exception as e:
        sprint("Failed to get settings", e)
        raise HTTPException(status_code = 500, detail = {"reason": str(e)})


@app.patch("/settings/{settings_type}/{resource_id}")
def save_settings(
    settings_type: Literal["user", "chat"],
    resource_id: str,
    request_data: dict[str, Any],
    db = Depends(get_session),
    token = Depends(verify_jwt_credentials),
):
    try:
        sprint(f"Saving {settings_type} settings for {resource_id}")
        user_id_hex, chat_id = SettingsManager.resolve_user_id_hex_and_chat_id(token)
        sprint(f"  User ID: {user_id_hex}, Chat ID: {chat_id}")
        settings_literal = "user_settings" if settings_type == "user" else "chat_settings"
        user_dao = UserCRUD(db)
        chat_config_dao = ChatConfigCRUD(db)
        settings_manager = SettingsManager(
            invoker_user_id_hex = user_id_hex,
            target_chat_id = chat_id,
            telegram_sdk = TelegramBotSDK(db),
            user_dao = user_dao,
            chat_config_dao = chat_config_dao,
            settings_type = settings_literal,
        )
        if settings_literal == "user_settings":
            open_ai_key = request_data.get("open_ai_key") or ""
            settings_manager.save_user_settings(resource_id, open_ai_key)
        else:
            language_name = request_data.get("language_name")
            if not language_name:
                raise ValueError("No language name provided")
            language_iso_code = request_data.get("language_iso_code")
            if not language_iso_code:
                raise ValueError("No language ISO code provided")
            reply_chance_percent = request_data.get("reply_chance_percent")
            if reply_chance_percent is None:
                raise ValueError("No reply chance percent provided")
            if not isinstance(reply_chance_percent, int):
                raise ValueError("Reply chance percent must be an integer")
            release_notifications = request_data.get("release_notifications")
            if not release_notifications:
                raise ValueError("No release notifications selection provided")
            settings_manager.save_chat_settings(
                chat_id = resource_id,
                language_name = language_name,
                language_iso_code = language_iso_code,
                reply_chance_percent = reply_chance_percent,
                release_notifications = str(release_notifications),
            )
        return {"status": "OK"}
    except Exception as e:
        sprint("Failed to save settings", e)
        raise HTTPException(status_code = 500, detail = {"reason": str(e)})
