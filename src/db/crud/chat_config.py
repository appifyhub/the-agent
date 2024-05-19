from sqlalchemy.orm import Session

from db.model.chat_config import ChatConfigDB
from db.schema.chat_config import ChatConfigCreate, ChatConfigUpdate


class ChatConfigCRUD:
    _db: Session

    def __init__(self, db: Session):
        self._db = db

    def get(self, chat_id: str):
        return self._db.query(ChatConfigDB).filter(
            chat_id == ChatConfigDB.chat_id
        ).first()

    def get_all(self, skip: int = 0, limit: int = 100):
        return self._db.query(ChatConfigDB).offset(skip).limit(limit).all()

    def create(self, chat_config: ChatConfigCreate):
        db_chat_config = ChatConfigDB(**chat_config.dict())
        self._db.add(db_chat_config)
        self._db.commit()
        self._db.refresh(db_chat_config)
        return db_chat_config

    def update(self, chat_id: str, update_data: ChatConfigUpdate):
        db_chat_config = self.get(chat_id)
        if db_chat_config:
            for key, value in update_data.dict().items():
                setattr(db_chat_config, key, value)
            self._db.commit()
            self._db.refresh(db_chat_config)
        return db_chat_config

    def delete(self, chat_id: str):
        db_chat_config = self.get(chat_id)
        if db_chat_config:
            self._db.delete(db_chat_config)
            self._db.commit()
        return db_chat_config
