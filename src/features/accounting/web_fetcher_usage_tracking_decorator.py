from time import time

from features.accounting.usage_tracking_service import UsageTrackingService
from features.external_tools.external_tool import ExternalTool, ToolType
from features.web_browsing.web_fetcher import WebFetcher


class WebFetcherUsageTrackingDecorator:

    __wrapped_fetcher: WebFetcher
    __tracking_service: UsageTrackingService
    __external_tool: ExternalTool
    __tool_purpose: ToolType

    def __init__(
        self,
        wrapped_fetcher: WebFetcher,
        tracking_service: UsageTrackingService,
        external_tool: ExternalTool,
        tool_purpose: ToolType,
    ):
        self.__wrapped_fetcher = wrapped_fetcher
        self.__tracking_service = tracking_service
        self.__external_tool = external_tool
        self.__tool_purpose = tool_purpose

    @property
    def url(self) -> str:
        return self.__wrapped_fetcher.url

    @property
    def html(self) -> str | None:
        return self.__wrapped_fetcher.html

    @property
    def json(self) -> dict | None:
        return self.__wrapped_fetcher.json

    def fetch_html(self) -> str | None:
        start_time = time()
        result = self.__wrapped_fetcher.fetch_html()
        runtime_seconds = time() - start_time

        self.__tracking_service.track_api_call(
            tool = self.__external_tool,
            tool_purpose = self.__tool_purpose,
            runtime_seconds = runtime_seconds,
        )

        return result

    def fetch_json(self) -> dict | None:
        start_time = time()
        result = self.__wrapped_fetcher.fetch_json()
        runtime_seconds = time() - start_time

        self.__tracking_service.track_api_call(
            tool = self.__external_tool,
            tool_purpose = self.__tool_purpose,
            runtime_seconds = runtime_seconds,
        )

        return result

    def __getattr__(self, name):
        return getattr(self.__wrapped_fetcher, name)
