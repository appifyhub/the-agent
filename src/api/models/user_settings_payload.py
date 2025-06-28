from typing import Any

from pydantic import BaseModel, field_validator


class UserSettingsPayload(BaseModel):
    open_ai_key: str | None = None
    anthropic_key: str | None = None
    perplexity_key: str | None = None
    replicate_key: str | None = None
    rapid_api_key: str | None = None
    coinmarketcap_key: str | None = None

    # noinspection PyNestedDecorators
    @field_validator(
        "open_ai_key",
        "anthropic_key",
        "perplexity_key",
        "replicate_key",
        "rapid_api_key",
        "coinmarketcap_key",
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
