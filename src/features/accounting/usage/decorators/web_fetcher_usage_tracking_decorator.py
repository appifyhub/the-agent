from time import time

from features.accounting.spending.spending_service import SpendingService
from features.accounting.usage.usage_tracking_service import UsageTrackingService
from features.external_tools.configured_tool import ConfiguredTool
from features.web_browsing.web_fetcher import WebFetcher


class WebFetcherUsageTrackingDecorator:

    __wrapped_fetcher: WebFetcher
    __tracking_service: UsageTrackingService
    __spending_service: SpendingService
    __configured_tool: ConfiguredTool

    def __init__(
        self,
        wrapped_fetcher: WebFetcher,
        tracking_service: UsageTrackingService,
        spending_service: SpendingService,
        configured_tool: ConfiguredTool,
    ):
        self.__wrapped_fetcher = wrapped_fetcher
        self.__tracking_service = tracking_service
        self.__spending_service = spending_service
        self.__configured_tool = configured_tool

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
        self.__spending_service.validate_pre_flight(self.__configured_tool)
        start_time = time()
        result = self.__wrapped_fetcher.fetch_html()
        runtime_seconds = time() - start_time

        record = self.__tracking_service.track_api_call(
            tool = self.__configured_tool.definition,
            tool_purpose = self.__configured_tool.purpose,
            runtime_seconds = runtime_seconds,
            payer_id = self.__configured_tool.payer_id,
            uses_credits = self.__configured_tool.uses_credits,
        )
        self.__spending_service.deduct(self.__configured_tool, record.total_cost_credits)

        return result

    def fetch_json(self) -> dict | None:
        self.__spending_service.validate_pre_flight(self.__configured_tool)
        start_time = time()
        result = self.__wrapped_fetcher.fetch_json()
        runtime_seconds = time() - start_time

        record = self.__tracking_service.track_api_call(
            tool = self.__configured_tool.definition,
            tool_purpose = self.__configured_tool.purpose,
            runtime_seconds = runtime_seconds,
            payer_id = self.__configured_tool.payer_id,
            uses_credits = self.__configured_tool.uses_credits,
        )
        self.__spending_service.deduct(self.__configured_tool, record.total_cost_credits)

        return result

    def __getattr__(self, name):
        return getattr(self.__wrapped_fetcher, name)
