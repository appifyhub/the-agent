from pydantic import BaseModel


class Video(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#video-messages"""
    id: str
    mime_type: str
    sha256: str
    caption: str | None = None
