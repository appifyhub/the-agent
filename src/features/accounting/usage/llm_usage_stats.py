from dataclasses import dataclass
from typing import Any

from langchain_core.messages import BaseMessage


@dataclass
class LLMUsageStats:
    input_tokens: int | None = None
    output_tokens: int | None = None
    search_tokens: int | None = None
    total_tokens: int | None = None
    remote_runtime_seconds: float | None = None

    @classmethod
    def from_response(cls, response: BaseMessage) -> "LLMUsageStats":
        # extract the metadata dictionary from the LLM response
        metadata = getattr(response, "response_metadata", None) or {}
        usage = metadata.get("token_usage") or metadata.get("usage") or {}
        if not usage:
            usage_metadata = getattr(response, "usage_metadata", None)
            if usage_metadata:
                usage = dict(usage_metadata) if hasattr(usage_metadata, "__dict__") else usage_metadata
        if not usage and any(key in metadata for key in ["input_tokens", "output_tokens", "total_tokens"]):
            usage_keys = ["input_tokens", "output_tokens", "total_tokens", "output_token_details"]
            usage = {k: v for k, v in metadata.items() if k in usage_keys}

        # get the normalized base stats, then decorate with model-specific stats
        normalized = cls.from_usage_metadata(usage)

        # enrich with Perplexity-specific stats
        return cls.decorate_with_perplexity_stats(normalized, usage)

    @classmethod
    def from_usage_metadata(cls, usage_metadata: Any | None) -> "LLMUsageStats":
        if usage_metadata is None:
            return cls()
        if hasattr(usage_metadata, "model_dump"):
            usage_metadata = usage_metadata.model_dump()
        elif hasattr(usage_metadata, "__dict__"):
            usage_metadata = usage_metadata.__dict__
        is_dict = isinstance(usage_metadata, dict)

        def get_val(key: str) -> Any:
            if is_dict:
                return usage_metadata.get(key)
            return getattr(usage_metadata, key, None)

        # @formatter:off
        input_tokens = get_val("input_tokens") \
                    or get_val("prompt_tokens") \
                    or get_val("prompt_token_count")
        output_tokens = get_val("output_tokens") \
                    or get_val("completion_tokens") \
                    or get_val("candidates_token_count")
        total_tokens = get_val("total_tokens") \
                    or get_val("total_token_count")
        remote_runtime_seconds = get_val("seconds") \
                    or get_val("duration")
        # @formatter:on

        # total is not provided explicitly, but we can calculate it
        if (input_tokens is not None or output_tokens is not None) and total_tokens is None:
            total_tokens = (input_tokens or 0) + (output_tokens or 0)

        return cls(
            input_tokens = input_tokens,
            output_tokens = output_tokens,
            total_tokens = total_tokens,
            remote_runtime_seconds = remote_runtime_seconds,
        )

    @classmethod
    def decorate_with_perplexity_stats(
        cls,
        base_stats: "LLMUsageStats",
        usage_metadata: dict | None,
    ) -> "LLMUsageStats":
        if not usage_metadata:
            return base_stats

        reasoning_tokens: int | None = None
        citation_tokens: int | None = None
        if isinstance(details := usage_metadata.get("output_token_details"), dict):
            if isinstance(r_tok := details.get("reasoning"), int):
                reasoning_tokens = r_tok
            if isinstance(c_tok := details.get("citation_tokens"), int):
                citation_tokens = c_tok

        # search tokens are a mix of citation and reasoning tokens (attempt at simplification)
        search_tokens: int | None = None
        if reasoning_tokens is not None:
            search_tokens = (search_tokens or 0) + reasoning_tokens
        if citation_tokens is not None:
            search_tokens = (search_tokens or 0) + citation_tokens

        # total tokens should include the new search tokens
        total_tokens: int | None = base_stats.total_tokens
        if search_tokens is not None:
            total_tokens = (total_tokens or 0) + search_tokens

        return cls(
            input_tokens = base_stats.input_tokens,
            output_tokens = base_stats.output_tokens,
            total_tokens = total_tokens,
            search_tokens = search_tokens,
            remote_runtime_seconds = base_stats.remote_runtime_seconds,
        )
