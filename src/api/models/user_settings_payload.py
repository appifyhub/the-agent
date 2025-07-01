from typing import Any

from pydantic import BaseModel, field_validator


class UserSettingsPayload(BaseModel):
    open_ai_key: str | None = None
    anthropic_key: str | None = None
    perplexity_key: str | None = None
    replicate_key: str | None = None
    rapid_api_key: str | None = None
    coinmarketcap_key: str | None = None
    tool_choice_llm: str | None = None
    tool_choice_vision: str | None = None
    tool_choice_hearing: str | None = None
    tool_choice_images: str | None = None
    tool_choice_search: str | None = None
    tool_choice_embedding: str | None = None
    tool_choice_api: str | None = None

    # noinspection PyNestedDecorators
    @field_validator(
        "open_ai_key",
        "anthropic_key",
        "perplexity_key",
        "replicate_key",
        "rapid_api_key",
        "coinmarketcap_key",
        "tool_choice_llm",
        "tool_choice_vision",
        "tool_choice_hearing",
        "tool_choice_images",
        "tool_choice_search",
        "tool_choice_embedding",
        "tool_choice_api",
        mode = "before",
    )
    @classmethod
    def trim_strings(cls, v: Any) -> Any:
        """Trim whitespace from string values, preserve None and empty strings"""
        if v is None:
            return None
        if isinstance(v, str):
            return v.strip()
        return v
