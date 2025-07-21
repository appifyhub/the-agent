from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, jwt
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from util.config import config
from util.safe_printer_mixin import sprint

__JWT_ALGORITHM = "HS256"

api_key_header = APIKeyHeader(name = "X-API-Key", auto_error = True)
telegram_auth_key_header = APIKeyHeader(name = "X-Telegram-Bot-Api-Secret-Token", auto_error = False)
jwt_header = HTTPBearer(bearerFormat = "JWT", auto_error = True)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if api_key != config.api_key.get_secret_value():
        raise HTTPException(status_code = HTTP_403_FORBIDDEN, detail = "Could not validate the API key")
    return api_key


def verify_telegram_auth_key(auth_key: str = Security(telegram_auth_key_header)) -> str:
    if config.telegram_must_auth and auth_key != config.telegram_auth_key.get_secret_value():
        raise HTTPException(status_code = HTTP_403_FORBIDDEN, detail = "Could not validate the Telegram auth token")
    return auth_key


def verify_jwt_credentials(authorization: HTTPAuthorizationCredentials = Security(jwt_header)) -> Dict[str, Any]:
    try:
        return verify_jwt_token(authorization.credentials)
    except ExpiredSignatureError as e:
        message = "Token has expired"
        sprint(message, e)
        raise HTTPException(
            status_code = HTTP_401_UNAUTHORIZED,
            detail = message,
            headers = {"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        message = "Could not validate access credentials"
        sprint(message, e)
        raise HTTPException(
            status_code = HTTP_401_UNAUTHORIZED,
            detail = message,
            headers = {"WWW-Authenticate": "Bearer"},
        )


def verify_jwt_token(token: str) -> Dict[str, Any]:
    return jwt.decode(
        token,
        config.jwt_secret_key.get_secret_value(),
        algorithms = [__JWT_ALGORITHM],
        options = {"verify_aud": False},
    )


def get_user_id_from_jwt(token_claims: Dict[str, Any] | None) -> str:
    if not token_claims:
        message = "Empty token"
        sprint(message)
        raise ValueError(message)
    user_id = token_claims.get("sub")
    if not user_id:
        message = "No user ID in token"
        sprint(message)
        raise ValueError(message)
    return user_id


def create_jwt_token(payload: Dict[str, Any], expires_in_minutes: int) -> str:
    now = datetime.now(timezone.utc)
    expires_in = timedelta(minutes = expires_in_minutes)
    to_encode = payload.copy()
    to_encode.update(
        {
            "exp": now + expires_in,
            "iat": now,
            "version": config.version,
        },
    )
    encoded_jwt = jwt.encode(to_encode, config.jwt_secret_key.get_secret_value(), algorithm = __JWT_ALGORITHM)
    return encoded_jwt
