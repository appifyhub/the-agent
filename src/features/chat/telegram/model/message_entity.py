from pydantic import BaseModel

from features.chat.telegram.model.user import User


class MessageEntity(BaseModel):
    """https://core.telegram.org/bots/api#messageentity"""
    type: str
    offset: int
    length: int
    url: str | None = None
    user: User | None = None
    language: str | None = None  # programming language of the code block
