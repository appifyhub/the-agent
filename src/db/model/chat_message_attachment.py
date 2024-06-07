from sqlalchemy import Column, String, Integer, ForeignKeyConstraint, PrimaryKeyConstraint
from sqlalchemy.orm import relationship

from db.sql import BaseModel


class ChatMessageAttachmentDB(BaseModel):
    __tablename__ = "chat_message_attachments"

    id = Column(String, primary_key = True)
    chat_id = Column(String, nullable = False)
    message_id = Column(String, nullable = False)
    size = Column(Integer, nullable = True)
    last_url = Column(String, nullable = True)
    last_url_until = Column(Integer, nullable = True)
    extension = Column(String, nullable = True)
    mime_type = Column(String, nullable = True)

    chat_message = relationship(
        "ChatMessageDB",
        back_populates = "attachments",
        foreign_keys = "[ChatMessageAttachmentDB.chat_id, ChatMessageAttachmentDB.message_id]",
    )

    __table_args__ = (
        PrimaryKeyConstraint("id"),
        ForeignKeyConstraint(
            ["chat_id", "message_id"],
            ["chat_messages.chat_id", "chat_messages.message_id"],
        ),
    )
