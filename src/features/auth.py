from datetime import timedelta, datetime, timezone
from typing import Dict, Any

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from starlette.status import HTTP_403_FORBIDDEN, HTTP_401_UNAUTHORIZED

from util.config import config

__JWT_ALGORITHM = "HS256"

api_key_header = APIKeyHeader(name = "X-API-Key", auto_error = True)
telegram_auth_key_header = APIKeyHeader(name = "X-Telegram-Bot-Api-Secret-Token", auto_error = False)
jwt_header = HTTPBearer(bearerFormat = "JWT", auto_error = True)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if api_key != config.api_key:
        raise HTTPException(status_code = HTTP_403_FORBIDDEN, detail = "Could not validate the API key")
    return api_key


def verify_telegram_auth_key(auth_key: str = Security(telegram_auth_key_header)) -> str:
    if config.telegram_must_auth and auth_key != config.telegram_auth_key:
        raise HTTPException(status_code = HTTP_403_FORBIDDEN, detail = "Could not validate the Telegram auth token")
    return auth_key


def verify_jwt_token(authorization: HTTPAuthorizationCredentials = Security(jwt_header)) -> Dict[str, Any]:
    try:
        return jwt.decode(authorization.credentials, config.jwt_secret_key, algorithms = [__JWT_ALGORITHM])
    except Exception as _:
        raise HTTPException(
            status_code = HTTP_401_UNAUTHORIZED,
            detail = "Could not validate access credentials",
            headers = {"WWW-Authenticate": "Bearer"},
        )


def create_jwt_token(payload: Dict[str, Any], expires_in: timedelta = timedelta(minutes = 5)) -> str:
    now = datetime.now(timezone.utc)
    to_encode = payload.copy()
    to_encode.update({"exp": now + expires_in, "iat": now})
    encoded_jwt = jwt.encode(to_encode, config.jwt_secret_key, algorithm = __JWT_ALGORITHM)
    return encoded_jwt
