from time import time
from typing import Any, Callable

from openai import OpenAI

from features.accounting.spending.spending_service import SpendingService
from features.accounting.usage.llm_usage_stats import LLMUsageStats
from features.accounting.usage.proxies.namespace_proxy import NamespaceProxy
from features.accounting.usage.usage_tracking_service import UsageTrackingService
from features.external_tools.configured_tool import ConfiguredTool
from util import log


class OpenAIUsageTrackingDecorator:

    __wrapped_client: OpenAI
    __tracking_service: UsageTrackingService
    __spending_service: SpendingService
    __configured_tool: ConfiguredTool

    def __init__(
        self,
        wrapped_client: OpenAI,
        tracking_service: UsageTrackingService,
        spending_service: SpendingService,
        configured_tool: ConfiguredTool,
    ):
        self.__wrapped_client = wrapped_client
        self.__tracking_service = tracking_service
        self.__spending_service = spending_service
        self.__configured_tool = configured_tool

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
            self.__spending_service.validate_pre_flight(self.__configured_tool)
            start_time = time()
            try:
                response = original_method(*args, **kwargs)
                runtime_seconds = time() - start_time
                self.__track_usage(response, runtime_seconds)
                return response
            except Exception:
                runtime_seconds = time() - start_time
                self.__track_failed_usage(runtime_seconds)
                raise
        return wrapper

    def __track_usage(self, response: Any, runtime_seconds: float) -> None:
        usage_metadata = getattr(response, "usage", None)
        usage_stats = LLMUsageStats.from_usage_metadata(usage_metadata)
        record = self.__tracking_service.track_text_model(
            tool = self.__configured_tool.definition,
            tool_purpose = self.__configured_tool.purpose,
            runtime_seconds = runtime_seconds,
            payer_id = self.__configured_tool.payer_id,
            uses_credits = self.__configured_tool.uses_credits,
            input_tokens = usage_stats.input_tokens,
            output_tokens = usage_stats.output_tokens,
            total_tokens = usage_stats.total_tokens,
            remote_runtime_seconds = usage_stats.remote_runtime_seconds,
        )
        self.__spending_service.deduct(self.__configured_tool, record.total_cost_credits)

    def __track_failed_usage(self, runtime_seconds: float) -> None:
        log.w(f"Tool call failed for {self.__configured_tool.definition.id}, tracking without deduction")
        self.__tracking_service.track_text_model(
            tool = self.__configured_tool.definition,
            tool_purpose = self.__configured_tool.purpose,
            runtime_seconds = runtime_seconds,
            payer_id = self.__configured_tool.payer_id,
            uses_credits = self.__configured_tool.uses_credits,
            is_failed = True,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self.__wrapped_client, name)
