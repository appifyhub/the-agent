from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ChatMessageBase(BaseModel):
    message_id: str
    author_id: UUID | None = None
    sent_at: datetime = datetime.now()
    text: str


class ChatMessageSave(ChatMessageBase):
    chat_id: UUID | None = None


class ChatMessage(ChatMessageBase):
    chat_id: UUID
    model_config = ConfigDict(from_attributes = True)
