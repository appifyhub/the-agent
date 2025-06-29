from sqlalchemy import Column, DateTime, ForeignKeyConstraint, PrimaryKeyConstraint, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from db.model.base import BaseModel


class ChatMessageDB(BaseModel):
    __tablename__ = "chat_messages"

    chat_id = Column(String, nullable = False)
    author_id = Column(UUID(as_uuid = True), nullable = True)
    message_id = Column(String, nullable = False)
    sent_at = Column(DateTime, default = func.now(), nullable = False)
    text = Column(Text, nullable = False)

    __table_args__ = (
        PrimaryKeyConstraint(chat_id, message_id, name = "pk_chat_message"),
        UniqueConstraint(chat_id, message_id, name = "uq_message_per_chat"),
        ForeignKeyConstraint([chat_id], ["chat_configs.chat_id"], name = "chat_messages_chat_id_fkey"),
        ForeignKeyConstraint([author_id], ["simulants.id"], name = "chat_messages_author_id_fkey"),
    )
