from datetime import datetime

from pydantic import ConfigDict, BaseModel


class ChatHistoryBase(BaseModel):
    chat_id: str
    message_id: str
    author_name: str | None = None
    author_username: str | None = None
    sent_at: datetime = datetime.now()
    text: str


class ChatHistoryCreate(ChatHistoryBase):
    pass


class ChatHistoryUpdate(BaseModel):
    text: str


class ChatHistory(ChatHistoryBase):
    model_config = ConfigDict(from_attributes = True)
