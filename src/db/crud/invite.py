from uuid import UUID

from sqlalchemy.orm import Session

from db.model.invite import InviteDB
from db.schema.invite import InviteCreate, InviteUpdate


class InviteCRUD:
    _db: Session

    def __init__(self, db: Session):
        self._db = db

    def get(self, invite_id: UUID):
        return self._db.query(InviteDB).filter(
            invite_id == InviteDB.id
        ).first()

    def get_all(self, skip: int = 0, limit: int = 100):
        return self._db.query(InviteDB).offset(skip).limit(limit).all()

    def create(self, invite: InviteCreate):
        db_invite = InviteDB(**invite.dict())
        self._db.add(db_invite)
        self._db.commit()
        self._db.refresh(db_invite)
        return db_invite

    def update(self, invite_id: UUID, update_data: InviteUpdate):
        db_invite = self.get(invite_id)
        if db_invite:
            for key, value in update_data.dict().items():
                setattr(db_invite, key, value)
            self._db.commit()
            self._db.refresh(db_invite)
        return db_invite

    def delete(self, invite_id: UUID):
        db_invite = self.get(invite_id)
        if db_invite:
            self._db.delete(db_invite)
            self._db.commit()
        return db_invite
