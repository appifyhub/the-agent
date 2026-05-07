import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from time import sleep
from typing import Any

from db.schema.tools_cache import ToolsCache, ToolsCacheSave
from di.di import DI
from features.accounting.usage.decorators.http_usage_tracking_decorator import HTTPUsageTrackingDecorator
from features.chat.supported_files import KNOWN_IMAGE_FORMATS
from features.external_tools.configured_tool import ConfiguredTool
from features.external_tools.external_tool import ToolType
from util import log
from util.config import config
from util.error_codes import EXTERNAL_EMPTY_RESPONSE
from util.errors import ExternalServiceError

CACHE_PREFIX = "twitter-status-fetcher"
CACHE_PREFIX_STRUCTURED = "twitter-status-fetcher-json"
CACHE_TTL = timedelta(weeks = 1)
RATE_LIMIT_DELAY_S = 2


@dataclass
class TweetMediaItem:
    url: str | None
    preview_url: str | None
    media_type: str  # "photo", "animated_gif", "video"


@dataclass
class TweetUserData:
    name: str | None
    handle: str
    bio: str | None
    profile_image_url: str | None


@dataclass
class TweetData:
    user: TweetUserData
    text: str
    language: str | None
    created_at: str | None
    media: list[TweetMediaItem] = field(default_factory = list)


class TwitterStatusFetcher:

    TWITTER_TOOL_TYPE: ToolType = ToolType.api_twitter
    VISION_TOOL_TYPE: ToolType = ToolType.vision

    __tweet_id: str
    __x_api_tool: ConfiguredTool
    __vision_tool: ConfiguredTool
    __http_client: HTTPUsageTrackingDecorator
    __di: DI

    def __init__(
        self,
        tweet_id: str,
        x_api_tool: ConfiguredTool,
        vision_tool: ConfiguredTool,
        di: DI,
    ):
        self.__tweet_id = tweet_id
        self.__x_api_tool = x_api_tool
        self.__vision_tool = vision_tool
        self.__http_client = di.tracked_http_get(x_api_tool)
        self.__di = di

    def execute(self) -> str:
        return self.as_text()

    def as_text(self) -> str:
        log.t(f"Fetching text content for tweet ID: {self.__tweet_id}")
        text_cache_key = self.__di.tools_cache_crud.create_key(CACHE_PREFIX, self.__tweet_id)
        cached = self.__get_cached_string(text_cache_key)
        if cached:
            return cached
        raw = self.__fetch_raw()
        resolved = self.__resolve_content(raw)
        self.__di.tools_cache_crud.save(
            ToolsCacheSave(
                key = text_cache_key,
                value = resolved,
                expires_at = datetime.now() + CACHE_TTL,
            ),
        )
        log.t(f"Text cache updated for key '{text_cache_key}'")
        return resolved

    def as_structured(self) -> TweetData:
        log.t(f"Fetching structured data for tweet ID: {self.__tweet_id}")
        raw = self.__fetch_raw()
        return self.__parse_structured(raw)

    def __fetch_raw(self) -> dict[str, Any]:
        raw_cache_key = self.__di.tools_cache_crud.create_key(CACHE_PREFIX_STRUCTURED, self.__tweet_id)
        cached_json = self.__get_cached_string(raw_cache_key)
        if cached_json:
            return json.loads(cached_json)

        api_url = f"https://api.x.com/2/tweets/{self.__tweet_id}"
        headers = {
            "Authorization": f"Bearer {self.__x_api_tool.token.get_secret_value()}",
        }
        params = {
            "expansions": "author_id,attachments.media_keys",
            "user.fields": "name,username,description,profile_image_url",
            "tweet.fields": "lang,text,created_at,note_tweet",
            "media.fields": "url,type,preview_image_url",
        }

        sleep(RATE_LIMIT_DELAY_S)
        response = self.__http_client.get(api_url, headers = headers, params = params, timeout = config.web_timeout_s)
        response.raise_for_status()
        response_json = response.json() or {}

        self.__di.tools_cache_crud.save(
            ToolsCacheSave(
                key = raw_cache_key,
                value = json.dumps(response_json),
                expires_at = datetime.now() + CACHE_TTL,
            ),
        )
        log.t(f"Raw cache updated for key '{raw_cache_key}'")
        return response_json

    def __get_cached_string(self, cache_key: str) -> str | None:
        log.t(f"Checking cache for key: '{cache_key}'")
        cache_entry_db = self.__di.tools_cache_crud.get(cache_key)
        if cache_entry_db:
            cache_entry = ToolsCache.model_validate(cache_entry_db)
            if not cache_entry.is_expired():
                log.t(f"Cache hit for key '{cache_key}'")
                return cache_entry.value
            log.t(f"Cache expired for key '{cache_key}'")
        log.t(f"Cache miss for key '{cache_key}'")
        return None

    def __parse_structured(self, response: dict[str, Any]) -> TweetData:
        post_data = response.get("data") or {}
        includes = response.get("includes") or {}

        users = includes.get("users") or []
        user_raw = users[0] if users else {}

        user = TweetUserData(
            name = user_raw.get("name") or None,
            handle = user_raw.get("username") or "unknown",
            bio = user_raw.get("description") or None,
            profile_image_url = user_raw.get("profile_image_url") or None,
        )

        media_items: list[TweetMediaItem] = []
        for m in includes.get("media") or []:
            media_type = m.get("type") or "photo"
            media_items.append(
                TweetMediaItem(
                    url = m.get("url") or None,
                    preview_url = m.get("preview_image_url") or None,
                    media_type = media_type,
                ),
            )

        note_tweet = post_data.get("note_tweet") or {}
        text = note_tweet.get("text") or post_data.get("text") or "<No text posted>"

        return TweetData(
            user = user,
            text = text,
            language = post_data.get("lang") or None,
            created_at = post_data.get("created_at") or None,
            media = media_items,
        )

    def __resolve_content(self, response: dict[str, Any]) -> str:
        try:
            post_data = response.get("data") or {}
            includes = response.get("includes") or {}

            post_language = post_data.get("lang") or "<No language given>"
            note_tweet = post_data.get("note_tweet") or {}
            post_text = note_tweet.get("text") or post_data.get("text") or "<No text posted>"

            users = includes.get("users") or []
            user = users[0] if users else {}
            name = user.get("name") or "<Anonymous>"
            username = user.get("username") or "anonymous"
            bio = user.get("description") or "<No user bio>"

            text_contents = "\n".join(
                [
                    f"A tweet-post by @{username} ({name}), language {post_language}:",
                    f"\n{post_text}\n",
                ],
            )
            photo_contents = self.__resolve_photo_contents(includes, text_contents)
            bio_contents = f"@{username}'s bio: \"{bio}\""

            sections = [text_contents]
            if photo_contents:
                sections.append("\n".join(photo_contents))
            sections.append(bio_contents)
            return "\n—\n".join(sections).strip()
        except Exception as e:
            raise ExternalServiceError("Error formatting tweet content", EXTERNAL_EMPTY_RESPONSE) from e

    def __resolve_photo_contents(self, includes: dict[str, Any], additional_context: str | None) -> list[str]:
        log.t(f"Resolving photo contents for tweet {self.__tweet_id}")
        media_list = includes.get("media") or []
        photo_descriptions: list[str] = []
        for i, media in enumerate(media_list):
            try:
                url = media.get("url") or None
                media_type = media.get("type") or None
                if url and media_type == "photo":
                    extension = url.lower().split(".")[-1]
                    mime_type = KNOWN_IMAGE_FORMATS.get(extension) if extension else KNOWN_IMAGE_FORMATS.get("png")
                    analyzer = self.__di.computer_vision_analyzer(
                        job_id = f"tweet-{self.__tweet_id}",
                        image_mime_type = str(mime_type),
                        configured_tool = self.__vision_tool,
                        image_url = url,
                        additional_context = f"[[ Tweet / X Post ]]\n\n{additional_context}",
                    )
                    description = analyzer.execute()
                    if description:
                        photo_descriptions.append(f"Photo [{i + 1}]: {url}\n{description}\n")
            except Exception as e:
                log.w(f"Error resolving photo {i + 1} from tweet {self.__tweet_id}", e)
        return photo_descriptions
