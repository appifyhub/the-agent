from pydantic import BaseModel

from chat.telegram.model.photo_size import PhotoSize


class Audio(BaseModel):
    """https://core.telegram.org/bots/api#audio"""
    file_id: str
    file_unique_id: str
    duration: int
    performer: str | None = None
    title: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    thumbnail: PhotoSize | None = None
