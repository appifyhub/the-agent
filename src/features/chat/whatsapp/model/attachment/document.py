from pydantic import BaseModel


class Document(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#document-messages"""
    id: str
    mime_type: str
    sha256: str
    filename: str | None = None
    caption: str | None = None
