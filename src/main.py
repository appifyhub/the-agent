import multiprocessing
import os
import random
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import UUID

import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import SecretStr
from starlette.responses import RedirectResponse

from api.auth import (
    get_chat_type_from_jwt,
    get_user_id_from_jwt,
    verify_api_key,
    verify_jwt_credentials,
    verify_telegram_auth_key,
    verify_whatsapp_auth_key,
)
from api.model.chat_settings_payload import ChatSettingsPayload
from api.model.release_output_payload import ReleaseOutputPayload
from api.model.sponsorship_payload import SponsorshipPayload
from api.model.user_settings_payload import UserSettingsPayload
from api.settings_controller import SettingsType
from db.model.chat_config import ChatConfigDB
from db.sql import get_session, initialize_db
from di.di import DI
from features.chat.telegram.currency_alert_responder import respond_with_currency_alerts
from features.chat.telegram.model.update import Update
from features.chat.telegram.release_summary_responder import respond_with_summary
from features.chat.telegram.telegram_update_responder import respond_to_update
from features.integrations.integrations import resolve_agent_user
from util import log
from util.config import Config, config


# noinspection PyUnusedLocal
@asynccontextmanager
async def lifespan(owner: FastAPI):
    process_name = multiprocessing.current_process().name
    worker_type = "main" if process_name == "MainProcess" else "worker"
    worker_info = f"[{worker_type}-{os.getpid()}] {process_name}"
    log.i(f"Lifecycle: Starting up {worker_info}")
    initialize_db()
    yield  # this holds the app alive until the server is shut down
    log.i(f"Lifecycle: Shutting down {worker_info}...")


app = FastAPI(
    docs_url = None,
    redoc_url = None,
    title = "The Agent's API",
    description = "This is the API service for The Agent.",
    debug = config.log_level in ["local", "trace", "debug"],
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
    _ = Depends(verify_telegram_auth_key),
) -> dict:
    offloader.add_task(respond_to_update, update)
    return {"status": "ok"}


@app.post("/whatsapp/chat-update")
async def whatsapp_chat_update(
    update: dict,
    _ = Depends(verify_whatsapp_auth_key),
) -> dict:
    log.d("Received WhatsApp update", update)
    return {"status": "ok"}


@app.post("/notify/price-alerts")
def notify_of_currency_alerts(
    db = Depends(get_session),
    _ = Depends(verify_api_key),
) -> dict:
    agent_user = resolve_agent_user(ChatConfigDB.ChatType.background)
    assert agent_user.id is not None
    di = DI(db, agent_user.id.hex)
    return respond_with_currency_alerts(di)


@app.post("/notify/release")
def notify_of_release(
    payload: ReleaseOutputPayload,
    db = Depends(get_session),
    _ = Depends(verify_api_key),
) -> dict:
    agent_user = resolve_agent_user(ChatConfigDB.ChatType.background)
    assert agent_user.id is not None
    di = DI(db, agent_user.id.hex)
    return respond_with_summary(payload, di)


@app.post("/task/clear-expired-cache")
def clear_expired_cache(
    db = Depends(get_session),
    _ = Depends(verify_api_key),
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
    db = Depends(get_session),
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
    db = Depends(get_session),
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
    db = Depends(get_session),
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
    db = Depends(get_session),
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
    db = Depends(get_session),
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
    db = Depends(get_session),
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
    db = Depends(get_session),
    token: dict[str, Any] = Depends(verify_jwt_credentials),
) -> dict:
    try:
        log.d(f"Sponsoring user from {resource_id}")
        invoker_id_hex = get_user_id_from_jwt(token)
        log.d(f"  Invoker ID: {invoker_id_hex}")
        di = DI(db, invoker_id_hex)
        di.sponsorships_controller.sponsor_user(resource_id, payload)
        return {"status": "OK"}
    except Exception as e:
        raise HTTPException(status_code = 500, detail = {"reason": log.e("Failed to sponsor user", e)})


@app.delete("/user/{resource_id}/sponsorships/{platform}/{platform_handle}")
def unsponsor_user(
    resource_id: str,
    platform: str,
    platform_handle: str,
    db = Depends(get_session),
    token: dict[str, Any] = Depends(verify_jwt_credentials),
) -> dict:
    try:
        log.d(f"Unsponsoring user from {resource_id}")
        invoker_id_hex = get_user_id_from_jwt(token)
        log.d(f"  Invoker ID: {invoker_id_hex}")
        di = DI(db, invoker_id_hex)
        di.sponsorships_controller.unsponsor_user(resource_id, platform, platform_handle)
        return {"status": "OK"}
    except Exception as e:
        raise HTTPException(status_code = 500, detail = {"reason": log.e("Failed to unsponsor user", e)})


@app.delete("/user/{resource_id}/sponsored")
def unsponsor_self(
    resource_id: str,
    db = Depends(get_session),
    token: dict[str, Any] = Depends(verify_jwt_credentials),
) -> dict:
    try:
        log.d(f"User {resource_id} is unsponsoring themselves")
        invoker_id_hex = get_user_id_from_jwt(token)
        log.d(f"  Invoker ID: {invoker_id_hex}")
        di = DI(db, invoker_id_hex)
        di.sponsorships_controller.unsponsor_self(resource_id)
        # Extract chat_type from JWT token
        chat_type_str = get_chat_type_from_jwt(token)
        chat_type = ChatConfigDB.ChatType.lookup(chat_type_str)
        if not chat_type:
            raise ValueError(f"Invalid chat type in the access token: {chat_type_str}")
        settings_link = di.settings_controller.create_settings_link(chat_type = chat_type)
        return {"settings_link": settings_link}
    except Exception as e:
        raise HTTPException(status_code = 500, detail = {"reason": log.e("Failed to unsponsor self", e)})


# The main runner
if __name__ == "__main__":
    if "--dev" in sys.argv:  # when running locally...
        os.environ["LOG_LEVEL"] = "debug"
        config.log_level = "debug"
        os.environ["API_KEY"] = "developer"
        config.api_key = SecretStr("developer")
        workers = 1
        reload = True
        print("INFO:     Launching in dev mode...")
    else:  # when running in production...
        # generate a random API key to prevent use of the default API key
        if config.api_key.get_secret_value() == Config.DEV_API_KEY:
            api_key = str(UUID(int = random.randint(0, 2 ** 128 - 1))).upper()
            os.environ["API_KEY"] = api_key
            config.api_key = SecretStr(api_key)
            print("WARN:     Generated a new API key!", config.api_key.get_secret_value(), file = sys.stderr)
        workers = 2
        reload = False
        # and run the database migrations
        print("INFO:     Running database migrations...")
        subprocess.run(["./tools/db_apply_migration.sh", "-y"], check = True)
        print("INFO:     Launching in production mode...")
    uvicorn_log_level = "debug" if config.log_level == "local" else config.log_level

    # get the service version
    if (version_file := Path("./.version")).exists():
        version_name = version_file.read_text().strip()
        if version_name:
            os.environ["VERSION"] = version_name
            config.version = version_name
            print("INFO:     Version file found", f"v{config.version}")
        else:
            print("ERROR:    Version file empty", file = sys.stderr)
    else:
        print("ERROR:    Version file not found, using dev version", file = sys.stderr)

    # finally, start the server
    uvicorn.run(
        "main:app",
        host = "0.0.0.0",
        port = 80,
        log_level = uvicorn_log_level,
        workers = workers,
        reload = reload,
    )
