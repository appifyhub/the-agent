from uuid import UUID

from sqlalchemy.orm import Session

from db.model.user import UserDB
from db.schema.user import UserCreate, UserUpdate


class UserCRUD:
    _db: Session

    def __init__(self, db: Session):
        self._db = db

    def get(self, user_id: UUID):
        return self._db.query(UserDB).filter(
            user_id == UserDB.id
        ).first()

    def get_all(self, skip: int = 0, limit: int = 100):
        return self._db.query(UserDB).offset(skip).limit(limit).all()

    def create(self, user: UserCreate):
        db_user = UserDB(**user.dict())
        self._db.add(db_user)
        self._db.commit()
        self._db.refresh(db_user)
        return db_user

    def update(self, user_id: UUID, update_data: UserUpdate):
        db_user = self.get(user_id)
        if db_user:
            for key, value in update_data.dict().items():
                setattr(db_user, key, value)
            self._db.commit()
            self._db.refresh(db_user)
        return db_user

    def delete(self, user_id: UUID):
        db_user = self.get(user_id)
        if db_user:
            self._db.delete(db_user)
            self._db.commit()
        return db_user
