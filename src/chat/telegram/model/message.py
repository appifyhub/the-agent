from typing import Optional

from pydantic import BaseModel, Field

from chat.telegram.model.attachment.audio import Audio
from chat.telegram.model.attachment.document import Document
from chat.telegram.model.attachment.photo_size import PhotoSize
from chat.telegram.model.attachment.voice import Voice
from chat.telegram.model.chat import Chat
from chat.telegram.model.message_entity import MessageEntity
from chat.telegram.model.text_quote import TextQuote
from chat.telegram.model.user import User


class Message(BaseModel):
    """https://core.telegram.org/bots/api#message"""
    chat: Chat
    message_id: int
    message_thread_id: int | None = None
    from_user: User | None = Field(None, alias = "from")
    text: str | None = None
    entities: list[MessageEntity] | None = None
    caption: str | None = None
    caption_entities: list[MessageEntity] | None = None
    reply_to_message: Optional["Message"] = None
    quote: TextQuote | None = None
    audio: Audio | None = None
    document: Document | None = None
    photo: list[PhotoSize] | None = None
    voice: Voice | None = None
    date: int
    edit_date: int | None = None


Message.model_rebuild()
