from pydantic import BaseModel


class Voice(BaseModel):
    """https://core.telegram.org/bots/api#voice"""
    file_id: str
    file_unique_id: str
    duration: int
    mime_type: str | None = None
    file_size: int | None = None
