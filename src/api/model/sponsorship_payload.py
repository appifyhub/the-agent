from pydantic import BaseModel, Field, field_validator


class SponsorshipPayload(BaseModel):
    platform_handle: str = Field(min_length = 1)
    platform: str

    @field_validator("platform_handle", mode = "before")
    @classmethod
    def strip_handle(cls, v: str) -> str:
        return v.strip()
