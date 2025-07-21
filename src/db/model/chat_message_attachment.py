from sqlalchemy import Column, ForeignKeyConstraint, Index, Integer, PrimaryKeyConstraint, String

from db.model.base import BaseModel


class ChatMessageAttachmentDB(BaseModel):
    __tablename__ = "chat_message_attachments"

    id = Column(String, primary_key = True)
    ext_id = Column(String, nullable = True)
    chat_id = Column(String, nullable = False)
    message_id = Column(String, nullable = False)
    size = Column(Integer, nullable = True)
    last_url = Column(String, nullable = True)
    last_url_until = Column(Integer, nullable = True)
    extension = Column(String, nullable = True)
    mime_type = Column(String, nullable = True)

    __table_args__ = (
        PrimaryKeyConstraint(id, name = "pk_chat_message_attachments"),
        ForeignKeyConstraint(
            [chat_id, message_id],
            ["chat_messages.chat_id", "chat_messages.message_id"],
            name = "chat_message_attachments_message_fkey",
        ),
        Index("idx_ext_id", ext_id),
    )
