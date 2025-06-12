from pydantic import BaseModel


class SponsorshipPayload(BaseModel):
    receiver_telegram_username: str
