from pydantic import BaseModel


class Document(BaseModel):
    """https://core.telegram.org/bots/api#document"""
    file_id: str
    file_unique_id: str
    file_name: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
