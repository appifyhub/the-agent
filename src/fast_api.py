from contextlib import asynccontextmanager
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse

from api.auth import get_user_id_from_jwt, verify_api_key, verify_jwt_credentials, verify_telegram_auth_key
from api.model.chat_settings_payload import ChatSettingsPayload
from api.model.release_output_payload import ReleaseOutputPayload
from api.model.sponsorship_payload import SponsorshipPayload
from api.model.user_settings_payload import UserSettingsPayload
from api.settings_controller import SettingsType
from db.sql import get_session, initialize_db
from di.di import DI
from features.chat.telegram.currency_alert_responder import respond_with_currency_alerts
from features.chat.telegram.model.update import Update
from features.chat.telegram.release_summary_responder import respond_with_summary
from features.chat.telegram.telegram_update_responder import respond_to_update
from features.prompting.prompt_library import TELEGRAM_BOT_USER
from util import log
from util.config import config


# noinspection PyUnusedLocal
@asynccontextmanager
async def lifespan(owner: FastAPI):
    log.i("Lifecycle: Starting up endpoints...")
    initialize_db()
    yield  # this holds the app alive until the server is shut down
    log.i("Lifecycle: Shutting down...")


app = FastAPI(
    docs_url = None,
    redoc_url = None,
    title = "The Agent's API",
    description = "This is the API service for The Agent.",
    debug = config.log_level in ["trace", "debug"],
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
def health() -> dict:
    return {"status": "ok", "version": config.version}


@app.post("/telegram/chat-update")
async def telegram_chat_update(
    update: Update,
    offloader: BackgroundTasks,
    _=Depends(verify_telegram_auth_key),
) -> dict:
    offloader.add_task(respond_to_update, update)
    return {"status": "ok"}


@app.post("/notify/price-alerts")
def notify_of_currency_alerts(
    db=Depends(get_session),
    _=Depends(verify_api_key),
) -> dict:
    assert TELEGRAM_BOT_USER.id is not None
    di = DI(db, TELEGRAM_BOT_USER.id.hex)
    return respond_with_currency_alerts(di)


@app.post("/notify/release")
def notify_of_release(
    payload: ReleaseOutputPayload,
    db=Depends(get_session),
    _=Depends(verify_api_key),
) -> dict:
    assert TELEGRAM_BOT_USER.id is not None
    di = DI(db, TELEGRAM_BOT_USER.id.hex)
    return respond_with_summary(payload, di)


@app.post("/task/clear-expired-cache")
def clear_expired_cache(
    db=Depends(get_session),
    _=Depends(verify_api_key),
) -> dict:
    try:
        di = DI(db)
        cleared_count = di.tools_cache_crud.delete_expired()
        log.i(f"Cleared expired cache entries: {cleared_count}")
        return {"cleared_entries_count": cleared_count}
    except Exception as e:
        raise HTTPException(status_code = 500, detail = {"reason ": log.e("Failed to clear expired cache", e)})


@app.get("/settings/{settings_type}/{resource_id}")
def get_settings(
    settings_type: SettingsType,
    resource_id: str,
    db=Depends(get_session),
    token: dict[str, Any] = Depends(verify_jwt_credentials),
) -> dict:
    try:
        log.d(f"Fetching '{settings_type}' settings for resource '{resource_id}'")
        invoker_id_hex = get_user_id_from_jwt(token)
        log.d(f"  Invoker ID: {invoker_id_hex}")
        di = DI(db, invoker_id_hex)
        if settings_type == "user":
            return di.settings_controller.fetch_user_settings(resource_id)
        else:
            return di.settings_controller.fetch_chat_settings(resource_id)
    except Exception as e:
        raise HTTPException(status_code = 500, detail = {"reason": log.e("Failed to get settings", e)})


@app.patch("/settings/user/{user_id_hex}")
def save_user_settings(
    user_id_hex: str,
    payload: UserSettingsPayload,
    db=Depends(get_session),
    token: dict[str, Any] = Depends(verify_jwt_credentials),
) -> dict:
    try:
        log.d(f"Saving user settings for user '{user_id_hex}'")
        invoker_id_hex = get_user_id_from_jwt(token)
        log.d(f"  Invoker ID: {invoker_id_hex}")
        di = DI(db, invoker_id_hex)
        di.settings_controller.save_user_settings(user_id_hex, payload)
        return {"status": "OK"}
    except Exception as e:
        raise HTTPException(status_code = 500, detail = {"reason": log.e("Failed to save user settings", e)})


@app.patch("/settings/chat/{chat_id}")
def save_chat_settings(
    chat_id: str,
    payload: ChatSettingsPayload,
    db=Depends(get_session),
    token: dict[str, Any] = Depends(verify_jwt_credentials),
) -> dict:
    try:
        log.d(f"Saving chat settings for chat '{chat_id}'")
        invoker_id_hex = get_user_id_from_jwt(token)
        log.d(f"  Invoker ID: {invoker_id_hex}")
        di = DI(db, invoker_id_hex)
        di.settings_controller.save_chat_settings(chat_id, payload)
        return {"status": "OK"}
    except Exception as e:
        raise HTTPException(status_code = 500, detail = {"reason": log.e("Failed to save chat settings", e)})


@app.get("/user/{resource_id}/chats")
def get_chats(
    resource_id: str,
    db=Depends(get_session),
    token: dict[str, Any] = Depends(verify_jwt_credentials),
) -> list[dict]:
    try:
        log.d(f"Fetching all chats for {resource_id}")
        invoker_id_hex = get_user_id_from_jwt(token)
        log.d(f"  Invoker ID: {invoker_id_hex}")
        di = DI(db, invoker_id_hex)
        return di.settings_controller.fetch_admin_chats(resource_id)
    except Exception as e:
        raise HTTPException(status_code = 500, detail = {"reason": log.e("Failed to get chats", e)})


@app.get("/settings/user/{resource_id}/tools")
def get_tools(
    resource_id: str,
    db=Depends(get_session),
    token: dict[str, Any] = Depends(verify_jwt_credentials),
) -> dict:
    try:
        log.d(f"Fetching tools for {resource_id}")
        invoker_id_hex = get_user_id_from_jwt(token)
        log.d(f"  Invoker ID: {invoker_id_hex}")
        di = DI(db, invoker_id_hex)
        return di.settings_controller.fetch_external_tools(resource_id)
    except Exception as e:
        raise HTTPException(status_code = 500, detail = {"reason": log.e("Failed to get external tools", e)})


@app.get("/user/{resource_id}/sponsorships")
def get_sponsorships(
    resource_id: str,
    db=Depends(get_session),
    token: dict[str, Any] = Depends(verify_jwt_credentials),
) -> dict:
    try:
        log.d(f"Fetching sponsorships for {resource_id}")
        invoker_id_hex = get_user_id_from_jwt(token)
        log.d(f"  Invoker ID: {invoker_id_hex}")
        di = DI(db, invoker_id_hex)
        sponsorships_controller = di.sponsorships_controller
        return sponsorships_controller.fetch_sponsorships(resource_id)
    except Exception as e:
        raise HTTPException(status_code = 500, detail = {"reason": log.e("Failed to get sponsorships", e)})


@app.post("/user/{resource_id}/sponsorships")
def sponsor_user(
    resource_id: str,
    payload: SponsorshipPayload,
    db=Depends(get_session),
    token: dict[str, Any] = Depends(verify_jwt_credentials),
) -> dict:
    try:
        log.d(f"Sponsoring user from {resource_id}")
        invoker_id_hex = get_user_id_from_jwt(token)
        log.d(f"  Invoker ID: {invoker_id_hex}")
        di = DI(db, invoker_id_hex)
        di.sponsorships_controller.sponsor_user(resource_id, payload.receiver_telegram_username)
        return {"status": "OK"}
    except Exception as e:
        raise HTTPException(status_code = 500, detail = {"reason": log.e("Failed to sponsor user", e)})


@app.delete("/user/{resource_id}/sponsorships/{receiver_telegram_username}")
def unsponsor_user(
    resource_id: str,
    receiver_telegram_username: str,
    db=Depends(get_session),
    token: dict[str, Any] = Depends(verify_jwt_credentials),
) -> dict:
    try:
        log.d(f"Unsponsoring user from {resource_id}")
        invoker_id_hex = get_user_id_from_jwt(token)
        log.d(f"  Invoker ID: {invoker_id_hex}")
        di = DI(db, invoker_id_hex)
        di.sponsorships_controller.unsponsor_user(resource_id, receiver_telegram_username)
        return {"status": "OK"}
    except Exception as e:
        raise HTTPException(status_code = 500, detail = {"reason": log.e("Failed to unsponsor user", e)})


@app.delete("/user/{resource_id}/sponsored")
def unsponsor_self(
    resource_id: str,
    db=Depends(get_session),
    token: dict[str, Any] = Depends(verify_jwt_credentials),
) -> dict:
    try:
        log.d(f"User {resource_id} is unsponsoring themselves")
        invoker_id_hex = get_user_id_from_jwt(token)
        log.d(f"  Invoker ID: {invoker_id_hex}")
        di = DI(db, invoker_id_hex)
        di.sponsorships_controller.unsponsor_self(resource_id)
        settings_link = di.settings_controller.create_settings_link()
        return {"settings_link": settings_link}
    except Exception as e:
        raise HTTPException(status_code = 500, detail = {"reason": log.e("Failed to unsponsor self", e)})
