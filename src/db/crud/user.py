from uuid import UUID

from sqlalchemy.orm import Session

from db.model.user import UserDB
from db.schema.user import UserCreate, UserUpdate


class UserCRUD:
    _db: Session

    def __init__(self, db: Session):
        self._db = db

    def get(self, user_id: UUID) -> UserDB | None:
        return self._db.query(UserDB).filter(
            user_id == UserDB.id
        ).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[UserDB]:
        # noinspection PyTypeChecker
        return self._db.query(UserDB).offset(skip).limit(limit).all()

    def create(self, create_data: UserCreate) -> UserDB:
        user = UserDB(**create_data.model_dump())
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def update(self, user_id: UUID, update_data: UserUpdate) -> UserDB | None:
        user = self.get(user_id)
        if user:
            for key, value in update_data.model_dump().items():
                setattr(user, key, value)
            self._db.commit()
            self._db.refresh(user)
        return user

    def delete(self, user_id: UUID) -> UserDB | None:
        user = self.get(user_id)
        if user:
            self._db.delete(user)
            self._db.commit()
        return user
