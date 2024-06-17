from pydantic import BaseModel

from features.chat.telegram.model.message_entity import MessageEntity


class TextQuote(BaseModel):
    """https://core.telegram.org/bots/api#textquote"""
    text: str
    position: int
    entities: list[MessageEntity] | None = None
