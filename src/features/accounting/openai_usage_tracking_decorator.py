from time import time
from typing import Any, Callable

from openai import OpenAI

from features.accounting.llm_usage_stats import LLMUsageStats
from features.accounting.namespace_proxy import NamespaceProxy
from features.accounting.usage_tracking_service import UsageTrackingService
from features.external_tools.external_tool import ExternalTool, ToolType


class OpenAIUsageTrackingDecorator:

    __wrapped_client: OpenAI
    __tracking_service: UsageTrackingService
    __external_tool: ExternalTool
    __tool_purpose: ToolType

    def __init__(
        self,
        wrapped_client: OpenAI,
        tracking_service: UsageTrackingService,
        external_tool: ExternalTool,
        tool_purpose: ToolType,
    ):
        self.__wrapped_client = wrapped_client
        self.__tracking_service = tracking_service
        self.__external_tool = external_tool
        self.__tool_purpose = tool_purpose

    @property
    def audio(self) -> Any:
        return NamespaceProxy(
            self.__wrapped_client.audio,
            self.__intercept_audio_call,
        )

    @property
    def embeddings(self) -> Any:
        return NamespaceProxy(
            self.__wrapped_client.embeddings,
            self.__intercept_embeddings_call,
        )

    def __intercept_audio_call(self, name: str, attr: Any) -> Any:
        if name == "transcriptions":
            return NamespaceProxy(attr, self.__intercept_transcriptions_call)
        return attr

    def __intercept_transcriptions_call(self, name: str, attr: Any) -> Any:
        if name == "create":
            return self.__wrap_usage_call(attr)
        return attr

    def __intercept_embeddings_call(self, name: str, attr: Any) -> Any:
        if name == "create":
            return self.__wrap_usage_call(attr)
        return attr

    def __wrap_usage_call(self, original_method: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time()
            response = original_method(*args, **kwargs)
            runtime_seconds = time() - start_time
            self.__track_usage(response, runtime_seconds)
            return response
        return wrapper

    def __track_usage(self, response: Any, runtime_seconds: float) -> None:
        usage_metadata = getattr(response, "usage", None)
        usage_stats = LLMUsageStats.from_usage_metadata(usage_metadata)
        self.__tracking_service.track_text_model(
            tool = self.__external_tool,
            tool_purpose = self.__tool_purpose,
            runtime_seconds = runtime_seconds,
            input_tokens = usage_stats.input_tokens,
            output_tokens = usage_stats.output_tokens,
            total_tokens = usage_stats.total_tokens,
            remote_runtime_seconds = usage_stats.remote_runtime_seconds,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self.__wrapped_client, name)
