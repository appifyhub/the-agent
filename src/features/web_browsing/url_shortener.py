from datetime import datetime

import requests
from requests import Response

from util import log
from util.config import config
from util.error_codes import EXTERNAL_EMPTY_RESPONSE, MISSING_URL, URL_SHORTENER_FAILED
from util.errors import ExternalServiceError, ValidationError


class UrlShortener:

    __long_url: str
    __custom_slug: str | None
    __valid_until: str | None
    __max_visits: int | None

    def __init__(
        self,
        long_url: str,
        custom_slug: str | None = None,
        valid_until: datetime | None = None,
        max_visits: int | None = None,
    ):
        if not long_url or not long_url.strip():
            raise ValidationError("long_url is required and cannot be empty", MISSING_URL)
        self.__long_url = long_url.strip()
        self.__custom_slug = custom_slug.strip() if custom_slug and custom_slug.strip() else None
        if valid_until:
            if valid_until.tzinfo is None:
                local_tz = datetime.now().astimezone().tzinfo
                valid_until = valid_until.replace(tzinfo = local_tz)
            self.__valid_until = valid_until.isoformat(timespec = "seconds")
        else:
            self.__valid_until = None
        self.__max_visits = max_visits

    def execute(self) -> str:
        response: Response | None = None
        try:
            log.t("Creating short URL...")
            base_url = config.url_shortener_base_url.rstrip("/")
            api_endpoint = f"{base_url}/rest/v3/short-urls"
            headers = {
                "X-Api-Key": config.url_shortener_api_key.get_secret_value(),
                "Content-Type": "application/json",
            }
            payload: dict[str, str | int] = {
                "longUrl": self.__long_url,
            }
            if self.__custom_slug:
                payload["customSlug"] = self.__custom_slug
            if self.__valid_until:
                payload["validUntil"] = self.__valid_until
            if self.__max_visits is not None:
                payload["maxVisits"] = self.__max_visits
            log.t("  Sending payload", payload)

            response = requests.post(api_endpoint, json = payload, headers = headers, timeout = config.web_timeout_s * 2)
            log.t(f"Response HTTP-{response.status_code} received!")
            response.raise_for_status()
            response_data = response.json()

            short_url = response_data.get("shortUrl")
            if not short_url:
                raise ExternalServiceError(f"API response missing 'shortUrl' field: {response_data}", EXTERNAL_EMPTY_RESPONSE)

            log.t("Short URL created successfully!")
            return str(short_url)
        except ExternalServiceError:
            raise  # don't re-wrap intentional errors in the generic handler below
        except Exception as e:
            response_text = {response.text if response is not None else "No response"}
            log.w("URL shortening failed!", response_text, e)
            raise ExternalServiceError("URL shortening failed", URL_SHORTENER_FAILED) from e
