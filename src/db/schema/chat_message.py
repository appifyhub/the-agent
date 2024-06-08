from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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


class ChatMessage(ChatMessageBase):
    model_config = ConfigDict(from_attributes = True)
