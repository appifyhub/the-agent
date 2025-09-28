from pydantic import BaseModel


class SponsorshipPayload(BaseModel):
    platform_handle: str
    platform: str
