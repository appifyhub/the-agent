from uuid import UUID

from sqlalchemy.orm import Session

from db.model.user import User as UserModel
from db.schema.user import UserCreate


class User:
    _db: Session

    def __init__(self, db: Session):
        self._db = db

    def get(self, user_id: UUID):
        return self._db.query(UserModel).filter(
            user_id == UserModel.id
        ).first()

    def get_all(self, skip: int = 0, limit: int = 100):
        return self._db.query(UserModel).offset(skip).limit(limit).all()

    def create(self, user: UserCreate):
        db_user = UserModel(**user.dict())
        self._db.add(db_user)
        self._db.commit()
        self._db.refresh(db_user)
        return db_user

    def update(self, user_id: UUID, update_data: UserCreate):
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
