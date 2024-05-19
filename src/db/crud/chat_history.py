from sqlalchemy.orm import Session

from db.model.chat_history import ChatHistoryDB
from db.schema.chat_history import ChatHistoryCreate, ChatHistoryUpdate


class ChatHistoryCRUD:
    _db: Session

    def __init__(self, db: Session):
        self._db = db

    def get(self, chat_id: str, message_id: str) -> ChatHistoryDB | None:
        return self._db.query(ChatHistoryDB).filter(
            chat_id == ChatHistoryDB.chat_id,
            message_id == ChatHistoryDB.message_id,
        ).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[ChatHistoryDB]:
        # noinspection PyTypeChecker
        return self._db.query(ChatHistoryDB).offset(skip).limit(limit).all()

    def create(self, chat_history: ChatHistoryCreate) -> ChatHistoryDB:
        db_chat_history = ChatHistoryDB(**chat_history.model_dump())
        self._db.add(db_chat_history)
        self._db.commit()
        self._db.refresh(db_chat_history)
        return db_chat_history

    def update(self, chat_id: str, message_id: str, update_data: ChatHistoryUpdate) -> ChatHistoryDB | None:
        db_chat_history = self.get(chat_id, message_id)
        if db_chat_history:
            for key, value in update_data.model_dump().items():
                setattr(db_chat_history, key, value)
            self._db.commit()
            self._db.refresh(db_chat_history)
        return db_chat_history

    def delete(self, chat_id: str, message_id: str) -> ChatHistoryDB | None:
        db_chat_history = self.get(chat_id, message_id)
        if db_chat_history:
            self._db.delete(db_chat_history)
            self._db.commit()
        return db_chat_history
