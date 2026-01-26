from time import time
from typing import Any, Callable

from replicate.client import Client
from replicate.prediction import Prediction

from features.accounting.proxies.namespace_proxy import NamespaceProxy
from features.accounting.service.usage_tracking_service import UsageTrackingService
from features.accounting.stats.image_usage_stats import ImageUsageStats
from features.external_tools.external_tool import ExternalTool, ToolType


class PredictionUsageTrackingDecorator:
    """We use this to wrap a prediction after calling .wait() on it."""

    __start_timestamp: float
    __wrapped_prediction: Prediction
    __tracking_service: UsageTrackingService
    __external_tool: ExternalTool
    __tool_purpose: ToolType
    __output_image_size: str | None
    __input_image_size: str | None
    __result: Any | None

    def __init__(
        self,
        wrapped_prediction: Prediction,
        tracking_service: UsageTrackingService,
        external_tool: ExternalTool,
        tool_purpose: ToolType,
        output_image_size: str | None = None,
        input_image_size: str | None = None,
    ):
        self.__start_timestamp = time()
        self.__wrapped_prediction = wrapped_prediction
        self.__tracking_service = tracking_service
        self.__external_tool = external_tool
        self.__tool_purpose = tool_purpose
        self.__output_image_size = output_image_size
        self.__input_image_size = input_image_size
        self.__result = None

    def wait(self) -> Any:
        if self.__result is not None:
            return self.__result

        result = self.__wrapped_prediction.wait()
        runtime_seconds = time() - self.__start_timestamp
        self.__track_usage(runtime_seconds)
        self.__result = result
        return result

    def __track_usage(self, runtime_seconds: float) -> None:
        stats = ImageUsageStats.from_replicate_prediction(self.__wrapped_prediction)

        self.__tracking_service.track_image_model(
            tool = self.__external_tool,
            tool_purpose = self.__tool_purpose,
            runtime_seconds = runtime_seconds,
            output_image_size = self.__output_image_size,
            input_image_size = self.__input_image_size,
            remote_runtime_seconds = stats.remote_runtime_seconds,
            input_tokens = stats.input_tokens,
            output_tokens = stats.output_tokens,
            total_tokens = stats.total_tokens,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self.__wrapped_prediction, name)


class ReplicateUsageTrackingDecorator:

    __wrapped_client: Client
    __tracking_service: UsageTrackingService
    __external_tool: ExternalTool
    __tool_purpose: ToolType
    __output_image_size: str | None
    __input_image_size: str | None

    def __init__(
        self,
        wrapped_client: Client,
        tracking_service: UsageTrackingService,
        external_tool: ExternalTool,
        tool_purpose: ToolType,
        output_image_size: str | None = None,
        input_image_size: str | None = None,
    ):
        self.__wrapped_client = wrapped_client
        self.__tracking_service = tracking_service
        self.__external_tool = external_tool
        self.__tool_purpose = tool_purpose
        self.__output_image_size = output_image_size
        self.__input_image_size = input_image_size

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
            prediction = original_method(**kwargs)
            return PredictionUsageTrackingDecorator(
                prediction,
                self.__tracking_service,
                self.__external_tool,
                self.__tool_purpose,
                self.__output_image_size,
                self.__input_image_size,
            )
        return wrapper

    def __getattr__(self, name: str) -> Any:
        return getattr(self.__wrapped_client, name)
