from pydantic import BaseModel


class Image(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#image-messages"""
    id: str
    mime_type: str
    sha256: str
    caption: str | None = None
