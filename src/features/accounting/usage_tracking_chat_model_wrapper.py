from time import time
from typing import Any, Sequence

from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import Runnable
from pydantic import BaseModel, PrivateAttr

from features.accounting.usage_tracking_service import UsageTrackingService
from features.external_tools.tool_choice_resolver import ConfiguredTool


class LLMUsageStats(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    @classmethod
    def from_provider_data(cls, usage: dict) -> "LLMUsageStats":
        if not usage:
            return cls()

        input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens") or usage.get("prompt_token_count")
        output_tokens = (
            usage.get("output_tokens") or usage.get("completion_tokens") or usage.get("candidates_token_count")
        )
        total_tokens = usage.get("total_tokens") or usage.get("total_token_count")

        if total_tokens is None and (input_tokens is not None or output_tokens is not None):
            total_tokens = (input_tokens or 0) + (output_tokens or 0)
            total_tokens = total_tokens if total_tokens > 0 else None

        return cls(
            input_tokens = input_tokens,
            output_tokens = output_tokens,
            total_tokens = total_tokens,
        )


class UsageTrackingRunnable(Runnable[LanguageModelInput, AIMessage]):
    """Wraps a Runnable to track usage metadata from responses."""

    _wrapped_runnable: Runnable[LanguageModelInput, AIMessage] = PrivateAttr()
    _configured_tool: ConfiguredTool = PrivateAttr()
    _tracking_service: UsageTrackingService = PrivateAttr()

    def __init__(
        self,
        wrapped_runnable: Runnable[LanguageModelInput, AIMessage],
        configured_tool: ConfiguredTool,
        tracking_service: UsageTrackingService,
    ):
        super().__init__()
        object.__setattr__(self, "_wrapped_runnable", wrapped_runnable)
        object.__setattr__(self, "_configured_tool", configured_tool)
        object.__setattr__(self, "_tracking_service", tracking_service)

    def invoke(self, input: LanguageModelInput, config = None, **kwargs) -> AIMessage:
        start_time = time()
        response = self._wrapped_runnable.invoke(input, config, **kwargs)
        runtime_seconds = int(time() - start_time)
        self.__log_usage(response, runtime_seconds)
        return response

    def __log_usage(self, response: BaseMessage, runtime_seconds: int) -> None:
        metadata = getattr(response, "response_metadata", None) or {}
        usage = metadata.get("token_usage") or metadata.get("usage") or {}

        tool, _, purpose = self._configured_tool

        if not usage:
            usage_metadata = getattr(response, "usage_metadata", None)
            if usage_metadata:
                usage = dict(usage_metadata) if hasattr(usage_metadata, "__dict__") else usage_metadata

        if not usage and any(key in metadata for key in ["input_tokens", "output_tokens", "total_tokens"]):
            usage_keys = ["input_tokens", "output_tokens", "total_tokens", "output_token_details"]
            usage = {k: v for k, v in metadata.items() if k in usage_keys}

        normalized_usage = LLMUsageStats.from_provider_data(usage)

        # Extract Perplexity-specific token breakdown
        reasoning_tokens = None
        citation_tokens = None
        search_tokens = None

        if "output_token_details" in usage and isinstance(usage["output_token_details"], dict):
            details = usage["output_token_details"]
            reasoning_tokens = details.get("reasoning", 0)
            citation_tokens = details.get("citation_tokens", 0)

            # Search tokens = everything else (excluding reasoning and citation_tokens)
            search_tokens = sum(v for k, v in details.items() if k not in ("reasoning", "citation_tokens"))

        # Add reasoning to input, citations to output
        input_tokens = normalized_usage.input_tokens
        output_tokens = normalized_usage.output_tokens

        if reasoning_tokens is not None:
            input_tokens = (normalized_usage.input_tokens or 0) + reasoning_tokens

        if citation_tokens is not None:
            output_tokens = (normalized_usage.output_tokens or 0) + citation_tokens

        self._tracking_service.track_llm(
            tool = tool,
            runtime_seconds = runtime_seconds,
            input_tokens = input_tokens,
            output_tokens = output_tokens,
            search_tokens = search_tokens,
            total_tokens = normalized_usage.total_tokens,
        )


class UsageTrackingChatModelWrapper(BaseChatModel):
    """Wraps a BaseChatModel to delegate calls and extract usage metadata."""

    _wrapped_model: BaseChatModel = PrivateAttr()
    _configured_tool: ConfiguredTool = PrivateAttr()
    _tracking_service: UsageTrackingService = PrivateAttr()

    def __init__(
        self,
        wrapped_model: BaseChatModel,
        configured_tool: ConfiguredTool,
        tracking_service: UsageTrackingService,
    ):
        super().__init__()
        object.__setattr__(self, "_wrapped_model", wrapped_model)
        object.__setattr__(self, "_configured_tool", configured_tool)
        object.__setattr__(self, "_tracking_service", tracking_service)

    def invoke(self, input: LanguageModelInput, config = None, **kwargs) -> AIMessage:
        start_time = time()
        response = self._wrapped_model.invoke(input, config, **kwargs)
        runtime_seconds = int(time() - start_time)
        self.__log_usage(response, runtime_seconds)
        return response

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> Runnable[LanguageModelInput, AIMessage]:
        wrapped_runnable = self._wrapped_model.bind_tools(tools, **kwargs)
        return UsageTrackingRunnable(wrapped_runnable, self._configured_tool, self._tracking_service)

    def __log_usage(self, response: BaseMessage, runtime_seconds: int) -> None:
        metadata = getattr(response, "response_metadata", None) or {}
        usage = metadata.get("token_usage") or metadata.get("usage") or {}

        tool, _, purpose = self._configured_tool

        if not usage:
            usage_metadata = getattr(response, "usage_metadata", None)
            if usage_metadata:
                usage = dict(usage_metadata) if hasattr(usage_metadata, "__dict__") else usage_metadata

        if not usage and any(key in metadata for key in ["input_tokens", "output_tokens", "total_tokens"]):
            usage_keys = ["input_tokens", "output_tokens", "total_tokens", "output_token_details"]
            usage = {k: v for k, v in metadata.items() if k in usage_keys}

        normalized_usage = LLMUsageStats.from_provider_data(usage)

        # Extract Perplexity-specific token breakdown
        reasoning_tokens = None
        citation_tokens = None
        search_tokens = None

        if "output_token_details" in usage and isinstance(usage["output_token_details"], dict):
            details = usage["output_token_details"]
            reasoning_tokens = details.get("reasoning", 0)
            citation_tokens = details.get("citation_tokens", 0)

            # Search tokens = everything else (excluding reasoning and citation_tokens)
            search_tokens = sum(v for k, v in details.items() if k not in ("reasoning", "citation_tokens"))

        # Add reasoning to input, citations to output
        input_tokens = normalized_usage.input_tokens
        output_tokens = normalized_usage.output_tokens

        if reasoning_tokens is not None:
            input_tokens = (normalized_usage.input_tokens or 0) + reasoning_tokens

        if citation_tokens is not None:
            output_tokens = (normalized_usage.output_tokens or 0) + citation_tokens

        self._tracking_service.track_llm(
            tool = tool,
            runtime_seconds = runtime_seconds,
            input_tokens = input_tokens,
            output_tokens = output_tokens,
            search_tokens = search_tokens,
            total_tokens = normalized_usage.total_tokens,
        )

    def _generate(self, *args: Any, **kwargs: Any) -> Any:
        return self._wrapped_model._generate(*args, **kwargs)

    @property
    def _llm_type(self) -> str:
        return getattr(self._wrapped_model, "_llm_type", "unknown")
