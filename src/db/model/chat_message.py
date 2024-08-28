from sqlalchemy import Column, String, DateTime, ForeignKey, Text, UniqueConstraint, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from db.sql import BaseModel


class ChatMessageDB(BaseModel):
    __tablename__ = "chat_messages"

    chat_id = Column(String, ForeignKey("chat_configs.chat_id"), nullable = False)
    author_id = Column(UUID(as_uuid = True), ForeignKey("simulants.id"), nullable = True)
    message_id = Column(String, nullable = False)
    sent_at = Column(DateTime, default = func.now(), nullable = False)
    text = Column(Text, nullable = False)

    __table_args__ = (
        PrimaryKeyConstraint(chat_id, message_id, name = "pk_chat_message"),
        UniqueConstraint(chat_id, message_id, name = "uq_message_per_chat"),
    )
