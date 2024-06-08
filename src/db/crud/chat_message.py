from sqlalchemy.orm import Session

from db.model.chat_message import ChatMessageDB
from db.schema.chat_message import ChatMessageCreate, ChatMessageUpdate


class ChatMessageCRUD:
    _db: Session

    def __init__(self, db: Session):
        self._db = db

    def get(self, chat_id: str, message_id: str) -> ChatMessageDB | None:
        return self._db.query(ChatMessageDB).filter(
            chat_id == ChatMessageDB.chat_id,
            message_id == ChatMessageDB.message_id,
        ).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[ChatMessageDB]:
        # noinspection PyTypeChecker
        return self._db.query(ChatMessageDB).offset(skip).limit(limit).all()

    def create(self, create_data: ChatMessageCreate) -> ChatMessageDB:
        chat_message = ChatMessageDB(**create_data.model_dump())
        self._db.add(chat_message)
        self._db.commit()
        self._db.refresh(chat_message)
        return chat_message

    def update(self, chat_id: str, message_id: str, update_data: ChatMessageUpdate) -> ChatMessageDB | None:
        chat_message = self.get(chat_id, message_id)
        if chat_message:
            for key, value in update_data.model_dump().items():
                setattr(chat_message, key, value)
            self._db.commit()
            self._db.refresh(chat_message)
        return chat_message

    def save(self, chat_id: str, message_id: str, data: ChatMessageCreate | ChatMessageUpdate) -> ChatMessageDB:
        updated_message = self.update(chat_id, message_id, data)
        if updated_message: return updated_message  # available only if update was successful
        return self.create(data)

    def delete(self, chat_id: str, message_id: str) -> ChatMessageDB | None:
        chat_message = self.get(chat_id, message_id)
        if chat_message:
            self._db.delete(chat_message)
            self._db.commit()
        return chat_message
