from sqlalchemy.orm import Session

from db.model.chat_message_attachment import ChatMessageAttachmentDB
from db.schema.chat_message_attachment import ChatMessageAttachmentCreate, ChatMessageAttachmentUpdate


class ChatMessageAttachmentCRUD:
    _db: Session

    def __init__(self, db: Session):
        self._db = db

    def get(self, attachment_id: str) -> ChatMessageAttachmentDB | None:
        return self._db.query(ChatMessageAttachmentDB).filter(
            attachment_id == ChatMessageAttachmentDB.id,
        ).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[ChatMessageAttachmentDB]:
        # noinspection PyTypeChecker
        return self._db.query(ChatMessageAttachmentDB).offset(skip).limit(limit).all()

    def create(self, create_data: ChatMessageAttachmentCreate) -> ChatMessageAttachmentDB:
        attachment = ChatMessageAttachmentDB(**create_data.model_dump())
        self._db.add(attachment)
        self._db.commit()
        self._db.refresh(attachment)
        return attachment

    def update(self, attachment_id: str, update_data: ChatMessageAttachmentUpdate) -> ChatMessageAttachmentDB | None:
        attachment = self.get(attachment_id)
        if attachment:
            for key, value in update_data.model_dump().items():
                setattr(attachment, key, value)
            self._db.commit()
            self._db.refresh(attachment)
        return attachment

    def delete(self, attachment_id: str) -> ChatMessageAttachmentDB | None:
        attachment = self.get(attachment_id)
        if attachment:
            self._db.delete(attachment)
            self._db.commit()
        return attachment
