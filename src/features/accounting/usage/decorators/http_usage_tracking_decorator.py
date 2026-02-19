from time import time
from typing import Any

import requests

from features.accounting.spending.spending_service import SpendingService
from features.accounting.usage.usage_tracking_service import UsageTrackingService
from features.external_tools.configured_tool import ConfiguredTool
from util import log


class HTTPUsageTrackingDecorator:

    __tracking_service: UsageTrackingService
    __spending_service: SpendingService
    __configured_tool: ConfiguredTool

    def __init__(
        self,
        tracking_service: UsageTrackingService,
        spending_service: SpendingService,
        configured_tool: ConfiguredTool,
    ):
        self.__tracking_service = tracking_service
        self.__spending_service = spending_service
        self.__configured_tool = configured_tool

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        self.__spending_service.validate_pre_flight(self.__configured_tool)
        start_time = time()
        try:
            response = requests.get(url, **kwargs)
            runtime_seconds = time() - start_time
            record = self.__tracking_service.track_api_call(
                tool = self.__configured_tool.definition,
                tool_purpose = self.__configured_tool.purpose,
                runtime_seconds = runtime_seconds,
                payer_id = self.__configured_tool.payer_id,
                uses_credits = self.__configured_tool.uses_credits,
            )
            self.__spending_service.deduct(self.__configured_tool, record.total_cost_credits)
            return response
        except Exception:
            runtime_seconds = time() - start_time
            log.w(f"Tool call failed for {self.__configured_tool.definition.id}, tracking without deduction")
            self.__tracking_service.track_api_call(
                tool = self.__configured_tool.definition,
                tool_purpose = self.__configured_tool.purpose,
                runtime_seconds = runtime_seconds,
                payer_id = self.__configured_tool.payer_id,
                uses_credits = self.__configured_tool.uses_credits,
                is_failed = True,
            )
            raise
