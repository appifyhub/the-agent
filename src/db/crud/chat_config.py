from sqlalchemy.orm import Session

from db.model.chat_config import ChatConfigDB
from db.schema.chat_config import ChatConfigCreate, ChatConfigUpdate


class ChatConfigCRUD:
    _db: Session

    def __init__(self, db: Session):
        self._db = db

    def get(self, chat_id: str) -> ChatConfigDB | None:
        return self._db.query(ChatConfigDB).filter(
            chat_id == ChatConfigDB.chat_id,
        ).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[ChatConfigDB]:
        # noinspection PyTypeChecker
        return self._db.query(ChatConfigDB).offset(skip).limit(limit).all()

    def create(self, create_data: ChatConfigCreate) -> ChatConfigDB:
        chat_config = ChatConfigDB(**create_data.model_dump())
        self._db.add(chat_config)
        self._db.commit()
        self._db.refresh(chat_config)
        return chat_config

    def update(self, chat_id: str, update_data: ChatConfigUpdate) -> ChatConfigDB | None:
        chat_config = self.get(chat_id)
        if chat_config:
            for key, value in update_data.model_dump().items():
                setattr(chat_config, key, value)
            self._db.commit()
            self._db.refresh(chat_config)
        return chat_config

    def save(self, chat_id: str, data: ChatConfigCreate | ChatConfigUpdate) -> ChatConfigDB:
        updated_config = self.update(chat_id, data)
        if updated_config: return updated_config  # available only if update was successful
        return self.create(data)

    def delete(self, chat_id: str) -> ChatConfigDB | None:
        chat_config = self.get(chat_id)
        if chat_config:
            self._db.delete(chat_config)
            self._db.commit()
        return chat_config
