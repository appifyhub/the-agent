from typing import Any

from pydantic import BaseModel, field_validator


class ChatSettingsPayload(BaseModel):
    language_name: str
    language_iso_code: str
    reply_chance_percent: int
    release_notifications: str

    # noinspection PyNestedDecorators
    @field_validator(
        "language_name",
        "language_iso_code",
        "release_notifications",
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

    # noinspection PyNestedDecorators
    @field_validator(
        "reply_chance_percent",
        mode = "after",
    )
    @classmethod
    def validate_reply_chance(cls, v: int) -> int:
        if not (0 <= v <= 100):
            raise ValueError("Reply chance percent must be between 0 and 100")
        return v
