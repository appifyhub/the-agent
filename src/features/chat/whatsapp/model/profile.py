from pydantic import BaseModel


class Profile(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages"""
    name: str | None = None
