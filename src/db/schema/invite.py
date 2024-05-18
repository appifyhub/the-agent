from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from db.schema.user import User


class InviteBase(BaseModel):
    sender_id: UUID
    receiver_id: UUID


class InviteCreate(InviteBase):
    pass


class Invite(InviteBase):
    id: UUID
    invited_at: datetime
    accepted_at: datetime | None = None
    sender: User
    receiver: User

    class Config:
        orm_mode = True
