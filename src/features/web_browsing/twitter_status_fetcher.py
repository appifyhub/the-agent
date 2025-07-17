from datetime import datetime, timedelta
from time import sleep
from typing import Any, Dict

import requests

from db.schema.tools_cache import ToolsCache, ToolsCacheSave
from di.di import DI
from features.chat.supported_files import KNOWN_IMAGE_FORMATS
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import TWITTER_API
from features.external_tools.tool_choice_resolver import ConfiguredTool
from features.images.computer_vision_analyzer import ComputerVisionAnalyzer
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

CACHE_PREFIX = "twitter-status-fetcher"
CACHE_TTL = timedelta(weeks = 52)
RATE_LIMIT_DELAY_S = 2


class TwitterStatusFetcher(SafePrinterMixin):
    DEFAULT_TWITTER_TOOL: ExternalTool = TWITTER_API
    TWITTER_TOOL_TYPE: ToolType = ToolType.api_twitter
    DEFAULT_VISION_TOOL: ExternalTool = ComputerVisionAnalyzer.DEFAULT_TOOL
    VISION_TOOL_TYPE: ToolType = ComputerVisionAnalyzer.TOOL_TYPE

    __tweet_id: str
    __twitter_api_tool: ConfiguredTool
    __vision_tool: ConfiguredTool
    __twitter_enterprise_tool: ConfiguredTool
    __di: DI

    def __init__(
        self,
        tweet_id: str,
        twitter_api_tool: ConfiguredTool,
        vision_tool: ConfiguredTool,
        twitter_enterprise_tool: ConfiguredTool,
        di: DI,
    ):
        super().__init__(config.verbose)
        self.__tweet_id = tweet_id
        self.__twitter_api_tool = twitter_api_tool
        self.__vision_tool = vision_tool
        self.__twitter_enterprise_tool = twitter_enterprise_tool
        self.__di = di

    def execute(self) -> str:
        self.sprint(f"Fetching content for tweet ID: {self.__tweet_id}")

        cache_key = self.__di.tools_cache_crud.create_key(CACHE_PREFIX, self.__tweet_id)
        cached_content = self.__get_cached_content(cache_key)
        if cached_content:
            return cached_content

        # prepare the base API contents
        twitter_api_tool, twitter_api_token, _ = self.__twitter_api_tool
        api_url = f"https://{twitter_api_tool.id}/base/apitools/tweetSimple"
        headers = {
            "X-RapidAPI-Key": twitter_api_token.get_secret_value(),
            "X-RapidAPI-Host": twitter_api_tool.id,
        }
        # prepare the enterprise API contents
        _, twitter_token, _ = self.__twitter_enterprise_tool
        enterprise_params = {
            "resFormat": "json",
            "id": self.__tweet_id,
            "apiKey": twitter_token.get_secret_value(),
            "cursor": "-1",
        }

        sleep(RATE_LIMIT_DELAY_S)
        response = requests.get(api_url, headers = headers, params = enterprise_params, timeout = config.web_timeout_s)
        response.raise_for_status()
        response = response.json() or {}

        resolved_content = self.__resolve_content(response)
        self.__di.tools_cache_crud.save(
            ToolsCacheSave(
                key = cache_key,
                value = resolved_content,
                expires_at = datetime.now() + CACHE_TTL,
            ),
        )
        self.sprint(f"Cache updated for key '{cache_key}'")
        return resolved_content

    def __get_cached_content(self, cache_key: str) -> str | None:
        self.sprint(f"Fetching cached content for key: '{cache_key}'")
        cache_entry_db = self.__di.tools_cache_crud.get(cache_key)
        if cache_entry_db:
            cache_entry = ToolsCache.model_validate(cache_entry_db)
            if not cache_entry.is_expired():
                self.sprint(f"Cache hit for key '{cache_key}'")
                return cache_entry.value
            self.sprint(f"Cache expired for key '{cache_key}'")
        self.sprint(f"Cache miss for key '{cache_key}'")
        return None

    def __resolve_content(self, response: Dict[str, Any]) -> str:
        try:
            tweet_result = response["data"]["data"]["tweetResult"]["result"]
            user = tweet_result["core"]["user_results"]["result"]["legacy"]
            tweet = tweet_result["legacy"]

            name = user.get("name") or "<Anonymous>"
            username = user.get("screen_name") or "anonymous"
            language_iso_code = tweet.get("lang") or "en"
            bio = user.get("description") or "<No bio>"
            post_text = tweet.get("full_text") or "<This tweet has no text>"

            text_contents = "\n".join(
                [
                    f"@{username} · {name}",
                    f'[Locale:{language_iso_code}] Bio: "{bio}"',
                    f"```\n{post_text}\n```",
                ],
            )
            photo_contents = self.__resolve_photo_contents(tweet, text_contents)
            return "\n".join([text_contents, photo_contents or ""]).strip()
        except Exception as e:
            message = "Error formatting tweet content"
            self.sprint(message, e)
            raise ValueError(f"{message}: {str(e)}")

    def __resolve_photo_contents(self, tweet: Dict[str, Any], additional_context: str | None) -> str | None:
        self.sprint(f"Resolving photo contents for tweet {self.__tweet_id}")
        attachments = tweet.get("extended_entities") or None
        if not attachments:
            return None
        media_attachments = attachments.get("media") or None
        if not media_attachments:
            return None
        photo_descriptions: list[str] = []
        for i, attachment in enumerate(media_attachments):
            try:
                url = attachment.get("media_url_https") or None
                type = attachment.get("type") or None
                if url and type == "photo":
                    extension = url.lower().split(".")[-1]
                    mime_type = (
                        KNOWN_IMAGE_FORMATS.get(extension) if extension else KNOWN_IMAGE_FORMATS.get("png")
                    )  # default to PNG
                    vision_tool, vision_token, _ = self.__vision_tool
                    analyzer = self.__di.computer_vision_analyzer(
                        job_id = f"tweet-{self.__tweet_id}",
                        image_mime_type = str(mime_type),
                        configured_tool = self.__vision_tool,
                        image_url = url,
                        additional_context = f"[[ Tweet / X Post ]]\n\n{additional_context}",
                    )
                    description = analyzer.execute()
                    photo_descriptions.append(f"---\nPhoto [{i + 1}]: {url}\n{description}")
            except Exception as e:
                self.sprint(f"Error resolving photo {i + 1} from tweet {self.__tweet_id}", e)
        return "\n".join(photo_descriptions) if photo_descriptions else None
