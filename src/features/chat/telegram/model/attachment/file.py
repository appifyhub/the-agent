from pydantic import BaseModel


class File(BaseModel):
    """https://core.telegram.org/bots/api#file"""
    file_id: str
    file_unique_id: str
    file_size: int | None = None
    file_path: str | None = None
