from time import time
from typing import Any, Callable

from xai_sdk import Client as XAISDKClient

from features.accounting.spending.spending_service import SpendingService
from features.accounting.usage.proxies.namespace_proxy import NamespaceProxy
from features.accounting.usage.usage_tracking_service import UsageTrackingService
from features.external_tools.configured_tool import ConfiguredTool
from util import log


class XAIUsageTrackingDecorator:

    __wrapped_client: XAISDKClient
    __tracking_service: UsageTrackingService
    __spending_service: SpendingService
    __configured_tool: ConfiguredTool
    __output_image_sizes: list[str] | None
    __input_image_sizes: list[str] | None

    def __init__(
        self,
        wrapped_client: XAISDKClient,
        tracking_service: UsageTrackingService,
        spending_service: SpendingService,
        configured_tool: ConfiguredTool,
        output_image_sizes: list[str] | None = None,
        input_image_sizes: list[str] | None = None,
    ):
        self.__wrapped_client = wrapped_client
        self.__tracking_service = tracking_service
        self.__spending_service = spending_service
        self.__configured_tool = configured_tool
        self.__output_image_sizes = output_image_sizes
        self.__input_image_sizes = input_image_sizes

    @property
    def image(self) -> Any:
        return NamespaceProxy(
            self.__wrapped_client.image,
            self.__intercept_image_call,
        )

    def __intercept_image_call(self, name: str, attr: Any) -> Any:
        if name == "sample":
            return self.__wrap_sample(attr)
        return attr

    def __wrap_sample(self, original_method: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            self.__spending_service.validate_pre_flight(
                self.__configured_tool,
                input_image_sizes = self.__input_image_sizes,
                output_image_sizes = self.__output_image_sizes,
            )
            start_time = time()
            try:
                response = original_method(*args, **kwargs)
                runtime_seconds = time() - start_time
                self.__track_usage(runtime_seconds)
                return response
            except Exception:
                runtime_seconds = time() - start_time
                self.__track_failed_usage(runtime_seconds)
                raise
        return wrapper

    def __track_usage(self, runtime_seconds: float) -> None:
        record = self.__tracking_service.track_image_model(
            tool = self.__configured_tool.definition,
            tool_purpose = self.__configured_tool.purpose,
            runtime_seconds = runtime_seconds,
            payer_id = self.__configured_tool.payer_id,
            uses_credits = self.__configured_tool.uses_credits,
            output_image_sizes = self.__output_image_sizes,
            input_image_sizes = self.__input_image_sizes,
        )
        self.__spending_service.deduct(self.__configured_tool, record.total_cost_credits)

    def __track_failed_usage(self, runtime_seconds: float) -> None:
        log.w(f"Tool call failed for {self.__configured_tool.definition.id}, tracking without deduction")
        self.__tracking_service.track_image_model(
            tool = self.__configured_tool.definition,
            tool_purpose = self.__configured_tool.purpose,
            runtime_seconds = runtime_seconds,
            payer_id = self.__configured_tool.payer_id,
            uses_credits = self.__configured_tool.uses_credits,
            output_image_sizes = self.__output_image_sizes,
            input_image_sizes = self.__input_image_sizes,
            is_failed = True,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self.__wrapped_client, name)
