from time import time
from typing import Any

import requests

from features.accounting.service.usage_tracking_service import UsageTrackingService
from features.external_tools.external_tool import ExternalTool, ToolType


class HTTPUsageTrackingDecorator:

    __tracking_service: UsageTrackingService
    __external_tool: ExternalTool
    __tool_purpose: ToolType

    def __init__(
        self,
        tracking_service: UsageTrackingService,
        external_tool: ExternalTool,
        tool_purpose: ToolType,
    ):
        self.__tracking_service = tracking_service
        self.__external_tool = external_tool
        self.__tool_purpose = tool_purpose

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        start_time = time()
        response = requests.get(url, **kwargs)
        runtime_seconds = time() - start_time

        self.__tracking_service.track_api_call(
            tool = self.__external_tool,
            tool_purpose = self.__tool_purpose,
            runtime_seconds = runtime_seconds,
        )

        return response
