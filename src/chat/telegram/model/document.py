from pydantic import BaseModel

from chat.telegram.model.photo_size import PhotoSize


class Document(BaseModel):
    """https://core.telegram.org/bots/api#document"""
    file_id: str
    file_unique_id: str
    thumbnail: PhotoSize | None = None
    file_name: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
