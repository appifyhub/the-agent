from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

from util.config import config

api_key_header = APIKeyHeader(name = "X-API-Key", auto_error = True)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if api_key != config.api_key:
        raise HTTPException(status_code = HTTP_403_FORBIDDEN, detail = "Could not validate the API key")
    return api_key
