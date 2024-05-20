from datetime import datetime

from pydantic import ConfigDict, BaseModel


class ChatMessageBase(BaseModel):
    chat_id: str
    message_id: str
    author_name: str | None = None
    author_username: str | None = None
    sent_at: datetime = datetime.now()
    text: str


class ChatMessageCreate(ChatMessageBase):
    pass


class ChatMessageUpdate(BaseModel):
    text: str


class ChatMessage(ChatMessageBase):
    model_config = ConfigDict(from_attributes = True)
