from datetime import datetime

from sqlalchemy.orm import Session

from db.model.tools_cache import ToolsCacheDB
from db.schema.tools_cache import ToolsCacheSave


class ToolsCacheCRUD:
    _db: Session

    def __init__(self, db: Session):
        self._db = db

    def get(self, key: str) -> ToolsCacheDB | None:
        return self._db.query(ToolsCacheDB).filter(
            key == ToolsCacheDB.key,
        ).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[ToolsCacheDB]:
        # noinspection PyTypeChecker
        return self._db.query(ToolsCacheDB).offset(skip).limit(limit).all()

    def create(self, create_data: ToolsCacheSave) -> ToolsCacheDB:
        tools_cache = ToolsCacheDB(**create_data.model_dump())
        self._db.add(tools_cache)
        self._db.commit()
        self._db.refresh(tools_cache)
        return tools_cache

    def update(self, update_data: ToolsCacheSave) -> ToolsCacheDB | None:
        tools_cache = self.get(update_data.key)
        if tools_cache:
            for key, value in update_data.model_dump().items():
                setattr(tools_cache, key, value)
            self._db.commit()
            self._db.refresh(tools_cache)
        return tools_cache

    def save(self, data: ToolsCacheSave) -> ToolsCacheDB:
        updated_cache = self.update(data)
        if updated_cache:
            return updated_cache
        return self.create(data)

    def delete(self, key: str) -> ToolsCacheDB | None:
        tools_cache = self.get(key)
        if tools_cache:
            self._db.delete(tools_cache)
            self._db.commit()
        return tools_cache

    def delete_expired(self) -> int:
        expired = self._db.query(ToolsCacheDB).filter(
            ToolsCacheDB.expires_at < datetime.now(),
        ).delete()
        self._db.commit()
        return expired
