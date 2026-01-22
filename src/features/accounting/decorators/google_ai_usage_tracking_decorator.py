from time import time
from typing import Any, Callable

from google.genai.client import Client as GoogleSDKClient
from google.genai.models import Models as GoogleSDKModels
from google.genai.types import GenerateContentResponse

from features.accounting.proxies.namespace_proxy import NamespaceProxy
from features.accounting.service.usage_tracking_service import UsageTrackingService
from features.accounting.stats.image_usage_stats import ImageUsageStats
from features.external_tools.external_tool import ExternalTool, ToolType


class GoogleAIUsageTrackingDecorator:

    __wrapped_client: GoogleSDKClient
    __tracking_service: UsageTrackingService
    __external_tool: ExternalTool
    __tool_purpose: ToolType
    __image_size: str | None

    def __init__(
        self,
        wrapped_client: GoogleSDKClient,
        tracking_service: UsageTrackingService,
        external_tool: ExternalTool,
        tool_purpose: ToolType,
        image_size: str | None = None,
    ):
        self.__wrapped_client = wrapped_client
        self.__tracking_service = tracking_service
        self.__external_tool = external_tool
        self.__tool_purpose = tool_purpose
        self.__image_size = image_size

    @property
    def models(self) -> GoogleSDKModels:
        return NamespaceProxy(
            self.__wrapped_client.models,
            self.__intercept_models_call,
        )  # type: ignore

    def __intercept_models_call(self, name: str, attr: Any) -> Any:
        if name == "generate_content":
            return self.__wrap_generate_content(attr)
        return attr

    def __wrap_generate_content(self, original_method: Callable[..., Any]) -> Callable[..., GenerateContentResponse]:
        def wrapper(*args: Any, **kwargs: Any) -> GenerateContentResponse:
            start_time = time()
            response: GenerateContentResponse = original_method(*args, **kwargs)
            runtime_seconds = time() - start_time
            self.__track_usage(response, runtime_seconds)
            return response
        return wrapper

    def __track_usage(self, response: GenerateContentResponse, runtime_seconds: float) -> None:
        usage_stats = ImageUsageStats.from_google_sdk_response(response)

        self.__tracking_service.track_image_model(
            tool = self.__external_tool,
            tool_purpose = self.__tool_purpose,
            runtime_seconds = runtime_seconds,
            image_size = self.__image_size,
            input_tokens = usage_stats.input_tokens,
            output_tokens = usage_stats.output_tokens,
            total_tokens = usage_stats.total_tokens,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self.__wrapped_client, name)
