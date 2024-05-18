from sqlalchemy.orm import Session

from db.model.chat_history import ChatHistory as ChatHistoryModel
from db.schema.chat_history import ChatHistoryCreate


class ChatHistory:
    _db: Session

    def __init__(self, db: Session):
        self._db = db

    def get_chat_history(self, chat_id: str, message_id: str):
        return self._db.query(ChatHistoryModel).filter(
            chat_id == ChatHistoryModel.chat_id,
            message_id == ChatHistoryModel.message_id,
        ).first()

    def get_chat_histories(self, skip: int = 0, limit: int = 100):
        return self._db.query(ChatHistoryModel).offset(skip).limit(limit).all()

    def create(self, chat_history: ChatHistoryCreate):
        db_chat_history = ChatHistoryModel(**chat_history.dict())
        self._db.add(db_chat_history)
        self._db.commit()
        self._db.refresh(db_chat_history)
        return db_chat_history

    def update(self, chat_id: str, message_id: str, update_data: ChatHistoryCreate):
        db_chat_history = self.get_chat_history(chat_id, message_id)
        if db_chat_history:
            for key, value in update_data.dict().items():
                setattr(db_chat_history, key, value)
            self._db.commit()
            self._db.refresh(db_chat_history)
        return db_chat_history

    def delete(self, chat_id: str, message_id: str):
        db_chat_history = self.get_chat_history(chat_id, message_id)
        if db_chat_history:
            self._db.delete(db_chat_history)
            self._db.commit()
        return db_chat_history
