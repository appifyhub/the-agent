from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

from util.config import config

api_key_header = APIKeyHeader(name = "X-API-Key", auto_error = True)
telegram_auth_key_header = APIKeyHeader(name = "X-Telegram-Bot-Api-Secret-Token", auto_error = False)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if api_key != config.api_key:
        raise HTTPException(status_code = HTTP_403_FORBIDDEN, detail = "Could not validate the API key")
    return api_key


def verify_telegram_auth_key(auth_key: str = Security(telegram_auth_key_header)) -> str:
    if config.telegram_must_auth and auth_key != config.telegram_auth_key:
        raise HTTPException(status_code = HTTP_403_FORBIDDEN, detail = "Could not validate the Telegram auth token")
    return auth_key
