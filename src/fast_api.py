from contextlib import asynccontextmanager
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse

from api.auth import get_user_id_from_jwt, verify_api_key, verify_jwt_credentials, verify_telegram_auth_key
from api.models.release_output_payload import ReleaseOutputPayload
from api.models.sponsorship_payload import SponsorshipPayload
from api.settings_controller import SettingsController, SettingsType
from api.sponsorships_controller import SponsorshipsController
from db.crud.chat_config import ChatConfigCRUD
from db.crud.price_alert import PriceAlertCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.tools_cache import ToolsCacheCRUD
from db.crud.user import UserCRUD
from db.sql import get_session, initialize_db
from features.chat.telegram.model.update import Update
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.chat.telegram.telegram_price_alert_responder import respond_with_announcements
from features.chat.telegram.telegram_summary_responder import respond_with_summary
from features.chat.telegram.telegram_update_responder import respond_to_update
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
    _ = Depends(verify_telegram_auth_key),
) -> dict:
    offloader.add_task(respond_to_update, update)
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
    settings_type: SettingsType,
    resource_id: str,
    db = Depends(get_session),
    token: dict[str, Any] = Depends(verify_jwt_credentials),
) -> dict:
    try:
        sprint(f"Fetching '{settings_type}' settings for resource '{resource_id}'")
        invoker_id_hex = get_user_id_from_jwt(token)
        sprint(f"  Invoker ID: {invoker_id_hex}")
        settings_controller = SettingsController(
            invoker_user_id_hex = invoker_id_hex,
            telegram_sdk = TelegramBotSDK(db),
            user_dao = UserCRUD(db),
            chat_config_dao = ChatConfigCRUD(db),
            sponsorship_dao = SponsorshipCRUD(db),
        )
        if settings_type == "user":
            return settings_controller.fetch_user_settings(resource_id)
        else:
            return settings_controller.fetch_chat_settings(resource_id)
    except Exception as e:
        sprint("Failed to get settings", e)
        raise HTTPException(status_code = 500, detail = {"reason": str(e)})


@app.patch("/settings/{settings_type}/{resource_id}")
def save_settings(
    settings_type: SettingsType,
    resource_id: str,
    request_data: dict[str, Any],
    db = Depends(get_session),
    token: dict[str, Any] = Depends(verify_jwt_credentials),
) -> dict:
    try:
        sprint(f"Saving '{settings_type}' settings for resource '{resource_id}'")
        invoker_id_hex = get_user_id_from_jwt(token)
        sprint(f"  Invoker ID: {invoker_id_hex}")
        settings_controller = SettingsController(
            invoker_user_id_hex = invoker_id_hex,
            telegram_sdk = TelegramBotSDK(db),
            user_dao = UserCRUD(db),
            chat_config_dao = ChatConfigCRUD(db),
            sponsorship_dao = SponsorshipCRUD(db),
        )
        if settings_type == "user":
            open_ai_key = request_data.get("open_ai_key") or ""
            settings_controller.save_user_settings(resource_id, open_ai_key)
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
            settings_controller.save_chat_settings(
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


@app.get("/user/{resource_id}/chats")
def get_chats(
    resource_id: str,
    db = Depends(get_session),
    token: dict[str, Any] = Depends(verify_jwt_credentials),
) -> list[dict]:
    try:
        sprint(f"Fetching all chats for {resource_id}")
        invoker_id_hex = get_user_id_from_jwt(token)
        sprint(f"  Invoker ID: {invoker_id_hex}")
        settings_controller = SettingsController(
            invoker_user_id_hex = invoker_id_hex,
            telegram_sdk = TelegramBotSDK(db),
            user_dao = UserCRUD(db),
            chat_config_dao = ChatConfigCRUD(db),
            sponsorship_dao = SponsorshipCRUD(db),
        )
        return settings_controller.fetch_admin_chats(resource_id)
    except Exception as e:
        sprint("Failed to get chats", e)
        raise HTTPException(status_code = 500, detail = {"reason": str(e)})


@app.get("/user/{resource_id}/sponsorships")
def get_sponsorships(
    resource_id: str,
    db = Depends(get_session),
    token: dict[str, Any] = Depends(verify_jwt_credentials),
) -> dict:
    try:
        sprint(f"Fetching sponsorships for {resource_id}")
        invoker_id_hex = get_user_id_from_jwt(token)
        sprint(f"  Invoker ID: {invoker_id_hex}")
        sponsorships_controller = SponsorshipsController(
            invoker_user_id_hex = invoker_id_hex,
            user_dao = UserCRUD(db),
            sponsorship_dao = SponsorshipCRUD(db),
            telegram_sdk = TelegramBotSDK(db),
            chat_config_dao = ChatConfigCRUD(db),
        )
        return sponsorships_controller.fetch_sponsorships(resource_id)
    except Exception as e:
        sprint("Failed to get sponsorships", e)
        raise HTTPException(status_code = 500, detail = {"reason": str(e)})


@app.post("/user/{resource_id}/sponsorships")
def sponsor_user(
    resource_id: str,
    payload: SponsorshipPayload,
    db = Depends(get_session),
    token: dict[str, Any] = Depends(verify_jwt_credentials),
) -> dict:
    try:
        sprint(f"Sponsoring user from {resource_id}")
        invoker_id_hex = get_user_id_from_jwt(token)
        sprint(f"  Invoker ID: {invoker_id_hex}")
        sponsorships_controller = SponsorshipsController(
            invoker_user_id_hex = invoker_id_hex,
            user_dao = UserCRUD(db),
            sponsorship_dao = SponsorshipCRUD(db),
            telegram_sdk = TelegramBotSDK(db),
            chat_config_dao = ChatConfigCRUD(db),
        )
        sponsorships_controller.sponsor_user(resource_id, payload.receiver_telegram_username)
        return {"status": "OK"}
    except Exception as e:
        sprint("Failed to sponsor user", e)
        raise HTTPException(status_code = 500, detail = {"reason": str(e)})


@app.delete("/user/{resource_id}/sponsorships/{receiver_telegram_username}")
def unsponsor_user(
    resource_id: str,
    receiver_telegram_username: str,
    db = Depends(get_session),
    token: dict[str, Any] = Depends(verify_jwt_credentials),
) -> dict:
    try:
        sprint(f"Unsponsoring user from {resource_id}")
        invoker_id_hex = get_user_id_from_jwt(token)
        sprint(f"  Invoker ID: {invoker_id_hex}")
        sponsorships_controller = SponsorshipsController(
            invoker_user_id_hex = invoker_id_hex,
            user_dao = UserCRUD(db),
            sponsorship_dao = SponsorshipCRUD(db),
            telegram_sdk = TelegramBotSDK(db),
            chat_config_dao = ChatConfigCRUD(db),
        )
        sponsorships_controller.unsponsor_user(resource_id, receiver_telegram_username)
        return {"status": "OK"}
    except Exception as e:
        sprint("Failed to unsponsor user", e)
        raise HTTPException(status_code = 500, detail = {"reason": str(e)})


@app.delete("/user/{resource_id}/sponsored")
def unsponsor_self(
    resource_id: str,
    db = Depends(get_session),
    token: dict[str, Any] = Depends(verify_jwt_credentials),
) -> dict:
    try:
        sprint(f"User {resource_id} is unsponsoring themselves")
        invoker_id_hex = get_user_id_from_jwt(token)
        sprint(f"  Invoker ID: {invoker_id_hex}")
        user_dao = UserCRUD(db)
        sponsorship_dao = SponsorshipCRUD(db)
        telegram_bot_sdk = TelegramBotSDK(db)
        chat_config_dao = ChatConfigCRUD(db)
        settings_controller = SettingsController(
            invoker_user_id_hex = resource_id,
            telegram_sdk = telegram_bot_sdk,
            user_dao = user_dao,
            chat_config_dao = chat_config_dao,
            sponsorship_dao = sponsorship_dao,
        )
        sponsorships_controller = SponsorshipsController(
            invoker_user_id_hex = invoker_id_hex,
            user_dao = user_dao,
            sponsorship_dao = sponsorship_dao,
            telegram_sdk = telegram_bot_sdk,
            chat_config_dao = chat_config_dao,
        )
        sponsorships_controller.unsponsor_self(resource_id)
        settings_link = settings_controller.create_settings_link()
        return {"settings_link": settings_link}
    except Exception as e:
        sprint("Failed to unsponsor self", e)
        raise HTTPException(status_code = 500, detail = {"reason": str(e)})
