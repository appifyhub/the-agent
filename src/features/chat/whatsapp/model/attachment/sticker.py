from pydantic import BaseModel


class Sticker(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#sticker-messages"""
    id: str
    mime_type: str
    sha256: str
