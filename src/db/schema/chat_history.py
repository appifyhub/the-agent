from datetime import datetime

from pydantic import BaseModel


class ChatHistoryBase(BaseModel):
    message_id: str
    author_name: str | None = None
    author_username: str | None = None
    sent_at: datetime
    text: str


class ChatHistoryCreate(ChatHistoryBase):
    pass


class ChatHistory(ChatHistoryBase):
    chat_id: str

    class Config:
        orm_mode = True
