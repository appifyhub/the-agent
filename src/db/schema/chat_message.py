from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import ConfigDict, BaseModel


class ChatMessageBase(BaseModel):
    chat_id: str
    message_id: str
    author_id: UUID | None = None
    sent_at: datetime = datetime.now()
    text: str


class ChatMessageCreate(ChatMessageBase):
    pass


class ChatMessageUpdate(BaseModel):
    text: str


# noinspection PyUnresolvedReferences
class ChatMessage(ChatMessageBase):
    attachments: List["ChatMessageAttachment"] = []
    model_config = ConfigDict(from_attributes = True)


# Importing here to avoid circular import issues
from db.schema.chat_message_attachment import ChatMessageAttachment

ChatMessage.model_rebuild()
