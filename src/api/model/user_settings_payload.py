from typing import Any

from pydantic import BaseModel, field_validator


class UserSettingsPayload(BaseModel):
    open_ai_key: str | None = None
    anthropic_key: str | None = None
    perplexity_key: str | None = None
    replicate_key: str | None = None
    rapid_api_key: str | None = None
    coinmarketcap_key: str | None = None

    tool_choice_chat: str | None = None
    tool_choice_reasoning: str | None = None
    tool_choice_copywriting: str | None = None
    tool_choice_vision: str | None = None
    tool_choice_hearing: str | None = None
    tool_choice_images_gen: str | None = None
    tool_choice_images_edit: str | None = None
    tool_choice_images_restoration: str | None = None
    tool_choice_images_inpainting: str | None = None
    tool_choice_images_background_removal: str | None = None
    tool_choice_search: str | None = None
    tool_choice_embedding: str | None = None
    tool_choice_api_fiat_exchange: str | None = None
    tool_choice_api_crypto_exchange: str | None = None
    tool_choice_api_twitter: str | None = None

    # noinspection PyNestedDecorators
    @field_validator(
        "open_ai_key",
        "anthropic_key",
        "perplexity_key",
        "replicate_key",
        "rapid_api_key",
        "coinmarketcap_key",
        "tool_choice_chat",
        "tool_choice_reasoning",
        "tool_choice_copywriting",
        "tool_choice_vision",
        "tool_choice_hearing",
        "tool_choice_images_gen",
        "tool_choice_images_edit",
        "tool_choice_images_restoration",
        "tool_choice_images_inpainting",
        "tool_choice_images_background_removal",
        "tool_choice_search",
        "tool_choice_embedding",
        "tool_choice_api_fiat_exchange",
        "tool_choice_api_crypto_exchange",
        "tool_choice_api_twitter",
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
