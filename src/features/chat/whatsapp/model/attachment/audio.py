from pydantic import BaseModel


class Audio(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#audio-messages"""
    id: str
    mime_type: str
    sha256: str
