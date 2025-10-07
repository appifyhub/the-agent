from pydantic import BaseModel


class Location(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#location-messages"""
    latitude: float
    longitude: float
    name: str | None = None
    address: str | None = None
