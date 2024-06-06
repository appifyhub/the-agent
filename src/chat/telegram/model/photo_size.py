from pydantic import BaseModel


class PhotoSize(BaseModel):
    """https://core.telegram.org/bots/api#photosize"""
    file_id: str
    file_unique_id: str
    width: int
    height: int
    file_size: int | None = None
