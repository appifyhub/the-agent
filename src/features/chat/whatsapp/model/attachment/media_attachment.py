from pydantic import BaseModel


class MediaAttachment(BaseModel):
    id: str
    caption: str | None = None
    mime_type: str | None = None
    sha256: str | None = None
    filename: str | None = None  # Only for documents
    voice: bool | None = None  # Only for audio/voice
