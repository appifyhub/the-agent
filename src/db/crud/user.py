from uuid import UUID

from sqlalchemy.orm import Session

from db.model.user import UserDB
from db.schema.user import UserSave


class UserCRUD:
    _db: Session

    def __init__(self, db: Session):
        self._db = db

    def get(self, user_id: UUID) -> UserDB | None:
        return self._db.query(UserDB).filter(
            user_id == UserDB.id,
        ).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[UserDB]:
        # noinspection PyTypeChecker
        return self._db.query(UserDB).offset(skip).limit(limit).all()

    def count(self) -> int:
        return self._db.query(UserDB).count()

    def get_by_telegram_user_id(self, telegram_user_id: int) -> UserDB | None:
        return self._db.query(UserDB).filter(
            telegram_user_id == UserDB.telegram_user_id
        ).first()

    def get_by_telegram_username(self, telegram_username: str) -> UserDB | None:
        return self._db.query(UserDB).filter(
            telegram_username == UserDB.telegram_username
        ).first()

    def create(self, create_data: UserSave) -> UserDB:
        user = UserDB(**create_data.model_dump())
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def update(self, update_data: UserSave) -> UserDB | None:
        if not update_data.id: return None  # can be called from 'save'
        user = self.get(update_data.id)
        if user:
            for key, value in update_data.model_dump().items():
                setattr(user, key, value)
            self._db.commit()
            self._db.refresh(user)
        return user

    def save(self, data: UserSave) -> UserDB:
        updated_user = self.update(data)
        if updated_user: return updated_user  # available only if update was successful
        return self.create(data)

    def delete(self, user_id: UUID) -> UserDB | None:
        user = self.get(user_id)
        if user:
            self._db.delete(user)
            self._db.commit()
        return user
