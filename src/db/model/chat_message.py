from sqlalchemy import Column, String, DateTime, ForeignKey, Text, UniqueConstraint, PrimaryKeyConstraint
from sqlalchemy.sql import func

from db.sql import BaseModel


class ChatMessageDB(BaseModel):
    __tablename__ = 'chat_messages'

    chat_id = Column(String, ForeignKey('chat_configs.chat_id'), nullable = False)
    message_id = Column(String, nullable = False)
    author_name = Column(String, nullable = True)
    author_username = Column(String, nullable = True)
    sent_at = Column(DateTime, default = func.now(), nullable = False)
    text = Column(Text, nullable = False)

    __table_args__ = (
        PrimaryKeyConstraint('chat_id', 'message_id', name = 'pk_chat_message'),
        UniqueConstraint('chat_id', 'message_id', name = 'uq_message_per_chat'),
    )
