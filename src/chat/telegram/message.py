from typing import Optional

from chat.telegram.audio import Audio
from chat.telegram.chat import Chat
from chat.telegram.document import Document
from chat.telegram.message_entity import MessageEntity
from chat.telegram.photo_size import PhotoSize
from chat.telegram.text_quote import TextQuote
from chat.telegram.user import User
from chat.telegram.voice import Voice


class Message:
    """https://core.telegram.org/bots/api#message"""
    message_id: int
    date: int
    message_thread_id: int | None
    reply_to_message: Optional["Message"]
    from_user: User | None
    chat: Chat | None
    quote: TextQuote | None
    edit_date: int | None
    text: str | None
    entities: list[MessageEntity] | None
    audio: Audio | None
    document: Document | None
    photo: list[PhotoSize] | None
    voice: Voice | None
    caption: str | None
    caption_entities: list[MessageEntity] | None

    def __init__(
        self,
        message_id: int,
        date: int,
        message_thread_id: int | None = None,
        reply_to_message: Optional["Message"] = None,
        from_user: User | None = None,
        chat: Chat | None = None,
        quote: TextQuote | None = None,
        edit_date: int | None = None,
        text: str | None = None,
        entities: list[MessageEntity] | None = None,
        audio: Audio | None = None,
        document: Document | None = None,
        photo: list[PhotoSize] | None = None,
        voice: Voice | None = None,
        caption: str | None = None,
        caption_entities: list[MessageEntity] | None = None,
    ):
        self.message_id = message_id
        self.date = date
        self.message_thread_id = message_thread_id
        self.reply_to_message = reply_to_message
        self.from_user = from_user
        self.chat = chat
        self.quote = quote
        self.edit_date = edit_date
        self.text = text
        self.entities = entities
        self.audio = audio
        self.document = document
        self.photo = photo
        self.voice = voice
        self.caption = caption
        self.caption_entities = caption_entities
