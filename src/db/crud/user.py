from typing import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from db.model.user import UserDB
from db.schema.user import UserSave
from util.error_codes import USER_NOT_FOUND
from util.errors import NotFoundError


class UserCRUD:

    _db: Session

    def __init__(self, db: Session):
        self._db = db

    def get(self, user_id: UUID) -> UserDB | None:
        return self._db.query(UserDB).filter(
            UserDB.id == user_id,
        ).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[UserDB]:
        # noinspection PyTypeChecker
        return self._db.query(UserDB).offset(skip).limit(limit).all()

    def count(self) -> int:
        return self._db.query(UserDB).count()

    def get_by_telegram_user_id(self, telegram_user_id: int) -> UserDB | None:
        return self._db.query(UserDB).filter(
            UserDB.telegram_user_id == telegram_user_id,
        ).first()

    def get_by_telegram_username(self, telegram_username: str) -> UserDB | None:
        return self._db.query(UserDB).filter(
            UserDB.telegram_username == telegram_username,
        ).first()

    def get_by_whatsapp_user_id(self, whatsapp_user_id: str) -> UserDB | None:
        return self._db.query(UserDB).filter(
            UserDB.whatsapp_user_id == whatsapp_user_id,
        ).first()

    def get_by_whatsapp_phone_number(self, whatsapp_phone_number: str) -> UserDB | None:
        return self._db.query(UserDB).filter(
            UserDB.whatsapp_phone_number == whatsapp_phone_number,
        ).first()

    def get_by_connect_key(self, connect_key: str) -> UserDB | None:
        return self._db.query(UserDB).filter(
            UserDB.connect_key == connect_key,
        ).first()

    def create(self, create_data: UserSave) -> UserDB:
        user = UserDB(**create_data.model_dump())
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def update(self, update_data: UserSave, commit: bool = True) -> UserDB | None:
        if not update_data.id:
            return None  # can be called from 'save'
        user = self.get(update_data.id)
        if user:
            for key, value in update_data.model_dump().items():
                setattr(user, key, value)
            self._db.flush()
            self._db.refresh(user)
            if commit:
                self._db.commit()
        return user

    def save(self, data: UserSave) -> UserDB:
        updated_user = self.update(data)
        if updated_user:
            return updated_user  # available only if update was successful
        return self.create(data)

    def update_locked(self, user_id: UUID, update_fn: Callable[[UserDB], None]) -> UserDB:
        user = self._db.query(UserDB).filter(
            UserDB.id == user_id,
        ).with_for_update().first()
        if user is None:
            raise NotFoundError(f"User {user_id} not found", USER_NOT_FOUND)
        update_fn(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def delete(self, user_id: UUID, commit: bool = True) -> UserDB | None:
        user = self.get(user_id)
        if user:
            self._db.delete(user)
            self._db.flush()
            if commit:
                self._db.commit()
        return user
