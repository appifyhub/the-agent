from datetime import datetime, timedelta

from di.di import DI
from features.external_tools.configured_tool import ConfiguredTool
from features.external_tools.external_tool import ToolType
from features.social_cards import card_renderer
from features.social_cards.theme import pick_theme
from features.web_browsing.photo_downloader import PhotoDownloader
from features.web_browsing.twitter_utils import resolve_tweet_id
from util import log
from util.error_codes import IMAGE_GENERATION_FAILED, WEB_FETCH_FAILED
from util.errors import ExternalServiceError, ValidationError


class SocialCardOrchestrator:

    TOOL_TYPE: ToolType = ToolType.api_twitter

    __x_api_tool: ConfiguredTool
    __di: DI

    def __init__(self, x_api_tool: ConfiguredTool, di: DI):
        self.__x_api_tool = x_api_tool
        self.__di = di

    def execute(self, url: str) -> str:
        tweet_id = resolve_tweet_id(url)
        if not tweet_id:
            raise ValidationError(f"Cannot resolve tweet ID from URL: {url}", WEB_FETCH_FAILED)

        fetcher = self.__di.twitter_status_fetcher(tweet_id, self.__x_api_tool, self.__x_api_tool)
        tweet = fetcher.as_structured()

        downloader = PhotoDownloader()

        profile_bytes: bytes | None = None
        if tweet.user.profile_image_url:
            bigger_url = tweet.user.profile_image_url.replace("_normal", "_bigger")
            profile_bytes = downloader.download(bigger_url)

        media_urls = [m.url or m.preview_url for m in tweet.media if m.url or m.preview_url]
        media_bytes = downloader.download_many([u for u in media_urls if u])

        theme = pick_theme(profile_bytes, media_bytes)

        short_url: str | None = None
        try:
            valid_until = datetime.now() + timedelta(days = 365)
            short_url = self.__di.url_shortener(url, valid_until = valid_until).execute()
        except Exception as e:
            log.w("URL shortening failed, using original URL", e)
            short_url = url

        try:
            png_bytes = card_renderer.render(
                tweet = tweet,
                theme = theme,
                profile_bytes = profile_bytes,
                media_bytes = media_bytes,
                short_url = short_url,
            )
        except Exception as e:
            raise ExternalServiceError("Card rendering failed", IMAGE_GENERATION_FAILED) from e

        return self.__di.image_uploader(binary_image = png_bytes).execute()
