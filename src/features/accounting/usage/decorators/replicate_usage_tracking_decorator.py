from time import time
from typing import Any, Callable

from replicate.client import Client
from replicate.prediction import Prediction

from features.accounting.spending.spending_service import SpendingService
from features.accounting.usage.image_usage_stats import ImageUsageStats
from features.accounting.usage.proxies.namespace_proxy import NamespaceProxy
from features.accounting.usage.usage_tracking_service import UsageTrackingService
from features.external_tools.configured_tool import ConfiguredTool


class PredictionUsageTrackingDecorator:

    __start_timestamp: float
    __wrapped_prediction: Prediction
    __tracking_service: UsageTrackingService
    __spending_service: SpendingService
    __configured_tool: ConfiguredTool
    __output_image_sizes: list[str] | None
    __input_image_sizes: list[str] | None
    __result: Any | None

    def __init__(
        self,
        wrapped_prediction: Prediction,
        tracking_service: UsageTrackingService,
        spending_service: SpendingService,
        configured_tool: ConfiguredTool,
        output_image_sizes: list[str] | None = None,
        input_image_sizes: list[str] | None = None,
    ):
        self.__start_timestamp = time()
        self.__wrapped_prediction = wrapped_prediction
        self.__tracking_service = tracking_service
        self.__spending_service = spending_service
        self.__configured_tool = configured_tool
        self.__output_image_sizes = output_image_sizes
        self.__input_image_sizes = input_image_sizes
        self.__result = None

    def wait(self) -> Any:
        if self.__result is not None:
            return self.__result
        try:
            result = self.__wrapped_prediction.wait()
            self.__result = result
            return result
        finally:
            runtime_seconds = time() - self.__start_timestamp
            self.__track_usage(runtime_seconds)

    def __track_usage(self, runtime_seconds: float) -> None:
        stats = ImageUsageStats.from_replicate_prediction(self.__wrapped_prediction)
        record = self.__tracking_service.track_image_model(
            tool = self.__configured_tool.definition,
            tool_purpose = self.__configured_tool.purpose,
            runtime_seconds = runtime_seconds,
            payer_id = self.__configured_tool.payer_id,
            uses_credits = self.__configured_tool.uses_credits,
            output_image_sizes = self.__output_image_sizes,
            input_image_sizes = self.__input_image_sizes,
            remote_runtime_seconds = stats.remote_runtime_seconds,
            input_tokens = stats.input_tokens,
            output_tokens = stats.output_tokens,
            total_tokens = stats.total_tokens,
        )
        self.__spending_service.deduct(self.__configured_tool, record.total_cost_credits)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.__wrapped_prediction, name)


class ReplicateUsageTrackingDecorator:

    __wrapped_client: Client
    __tracking_service: UsageTrackingService
    __spending_service: SpendingService
    __configured_tool: ConfiguredTool
    __output_image_sizes: list[str] | None
    __input_image_sizes: list[str] | None

    def __init__(
        self,
        wrapped_client: Client,
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
    def predictions(self) -> Any:
        return NamespaceProxy(
            self.__wrapped_client.predictions,
            self.__intercept_predictions_call,
        )

    def __intercept_predictions_call(self, name: str, attr: Any) -> Any:
        if name == "create":
            return self.__wrap_create(attr)
        return attr

    def __wrap_create(self, original_method: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(**kwargs: Any) -> PredictionUsageTrackingDecorator:
            self.__spending_service.validate_pre_flight(
                self.__configured_tool,
                input_image_sizes = self.__input_image_sizes,
                output_image_sizes = self.__output_image_sizes,
            )
            prediction = original_method(**kwargs)
            return PredictionUsageTrackingDecorator(
                prediction,
                self.__tracking_service,
                self.__spending_service,
                self.__configured_tool,
                self.__output_image_sizes,
                self.__input_image_sizes,
            )
        return wrapper

    def __getattr__(self, name: str) -> Any:
        return getattr(self.__wrapped_client, name)
