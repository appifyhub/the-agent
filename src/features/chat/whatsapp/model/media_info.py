from pydantic import BaseModel


class MediaInfo(BaseModel):
    """WhatsApp media information from Graph API"""
    id: str
    url: str
    mime_type: str | None = None
    sha256: str | None = None
    file_size: int | None = None
