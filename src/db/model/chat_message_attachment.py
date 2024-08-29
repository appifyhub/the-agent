from sqlalchemy import Column, String, Integer, ForeignKeyConstraint, PrimaryKeyConstraint

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

    __table_args__ = (
        PrimaryKeyConstraint(id),
        ForeignKeyConstraint(
            [chat_id, message_id],
            ["chat_messages.chat_id", "chat_messages.message_id"],
        ),
    )
