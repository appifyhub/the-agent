from pydantic import BaseModel, Field, field_validator


class CreditTransferPayload(BaseModel):
    platform: str = Field(min_length = 1)
    platform_handle: str = Field(min_length = 1)
    amount: float = Field(gt = 0)
    note: str | None = None

    @field_validator("platform", "platform_handle", mode = "before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()

    @field_validator("platform_handle", mode = "after")
    @classmethod
    def strip_handle_prefixes(cls, v: str) -> str:
        return v.lstrip("@").lstrip("+").lstrip("#")
