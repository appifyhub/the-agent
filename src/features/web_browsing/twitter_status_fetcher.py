from datetime import datetime, timedelta
from time import sleep
from typing import Any, Dict

from db.schema.tools_cache import ToolsCache, ToolsCacheSave
from di.di import DI
from features.accounting.usage.decorators.http_usage_tracking_decorator import HTTPUsageTrackingDecorator
from features.chat.supported_files import KNOWN_IMAGE_FORMATS
from features.external_tools.configured_tool import ConfiguredTool
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import X_READ_POST
from features.images.computer_vision_analyzer import ComputerVisionAnalyzer
from util import log
from util.config import config
from util.error_codes import EXTERNAL_EMPTY_RESPONSE
from util.errors import ExternalServiceError

CACHE_PREFIX = "twitter-status-fetcher"
CACHE_TTL = timedelta(weeks = 52)
RATE_LIMIT_DELAY_S = 2


class TwitterStatusFetcher:

    DEFAULT_TWITTER_TOOL: ExternalTool = X_READ_POST
    TWITTER_TOOL_TYPE: ToolType = ToolType.api_twitter
    DEFAULT_VISION_TOOL: ExternalTool = ComputerVisionAnalyzer.DEFAULT_TOOL
    VISION_TOOL_TYPE: ToolType = ComputerVisionAnalyzer.TOOL_TYPE

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
        log.t(f"Fetching content for tweet ID: {self.__tweet_id}")

        cache_key = self.__di.tools_cache_crud.create_key(CACHE_PREFIX, self.__tweet_id)
        cached_content = self.__get_cached_content(cache_key)
        if cached_content:
            return cached_content

        api_url = f"https://api.x.com/2/tweets/{self.__tweet_id}"
        headers = {
            "Authorization": f"Bearer {self.__x_api_tool.token.get_secret_value()}",
        }
        params = {
            "expansions": "author_id,attachments.media_keys",
            "user.fields": "name,username,description",
            "tweet.fields": "lang,text",
            "media.fields": "url,type",
        }

        sleep(RATE_LIMIT_DELAY_S)
        response = self.__http_client.get(api_url, headers = headers, params = params, timeout = config.web_timeout_s)
        response.raise_for_status()
        response_json = response.json() or {}

        resolved_content = self.__resolve_content(response_json)
        self.__di.tools_cache_crud.save(
            ToolsCacheSave(
                key = cache_key,
                value = resolved_content,
                expires_at = datetime.now() + CACHE_TTL,
            ),
        )
        log.t(f"Cache updated for key '{cache_key}'")

        return resolved_content

    def __get_cached_content(self, cache_key: str) -> str | None:
        log.t(f"Fetching cached content for key: '{cache_key}'")
        cache_entry_db = self.__di.tools_cache_crud.get(cache_key)
        if cache_entry_db:
            cache_entry = ToolsCache.model_validate(cache_entry_db)
            if not cache_entry.is_expired():
                log.t(f"Cache hit for key '{cache_key}'")
                return cache_entry.value
            log.t(f"Cache expired for key '{cache_key}'")
        log.t(f"Cache miss for key '{cache_key}'")
        return None

    def __resolve_content(self, response: Dict[str, Any]) -> str:
        try:
            post_data = response.get("data") or {}
            includes = response.get("includes") or {}

            post_language = post_data.get("lang") or "<No language given>"
            post_text = post_data.get("text") or "<No text posted>"

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

    def __resolve_photo_contents(self, includes: Dict[str, Any], additional_context: str | None) -> list[str]:
        log.t(f"Resolving photo contents for tweet {self.__tweet_id}")
        media_list = includes.get("media") or []
        photo_descriptions: list[str] = []
        for i, media in enumerate(media_list):
            try:
                url = media.get("url") or None
                media_type = media.get("type") or None
                if url and media_type == "photo":
                    extension = url.lower().split(".")[-1]
                    mime_type = (
                        KNOWN_IMAGE_FORMATS.get(extension) if extension else KNOWN_IMAGE_FORMATS.get("png")
                    )
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
