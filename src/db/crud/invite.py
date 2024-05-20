from uuid import UUID

from sqlalchemy.orm import Session

from db.model.invite import InviteDB
from db.schema.invite import InviteCreate, InviteUpdate


class InviteCRUD:
    _db: Session

    def __init__(self, db: Session):
        self._db = db

    def get(self, sender_id: UUID, receiver_id: UUID) -> InviteDB | None:
        return self._db.query(InviteDB).filter(
            sender_id == InviteDB.sender_id,
            receiver_id == InviteDB.receiver_id,
        ).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[InviteDB]:
        # noinspection PyTypeChecker
        return self._db.query(InviteDB).offset(skip).limit(limit).all()

    def create(self, create_data: InviteCreate) -> InviteDB:
        invite = InviteDB(**create_data.model_dump())
        self._db.add(invite)
        self._db.commit()
        self._db.refresh(invite)
        return invite

    def update(self, sender_id: UUID, receiver_id: UUID, update_data: InviteUpdate) -> InviteDB | None:
        invite = self.get(sender_id, receiver_id)
        if invite:
            for key, value in update_data.model_dump().items():
                setattr(invite, key, value)
            self._db.commit()
            self._db.refresh(invite)
        return invite

    def delete(self, sender_id: UUID, receiver_id: UUID) -> InviteDB | None:
        invite = self.get(sender_id, receiver_id)
        if invite:
            self._db.delete(invite)
            self._db.commit()
        return invite
