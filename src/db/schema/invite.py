from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, BaseModel


class InviteBase(BaseModel):
    sender_id: UUID
    receiver_id: UUID


class InviteCreate(InviteBase):
    pass


class InviteUpdate(BaseModel):
    accepted_at: datetime


# noinspection PyUnresolvedReferences
class Invite(InviteBase):
    invited_at: datetime
    accepted_at: datetime | None = None
    sender: "User"
    receiver: "User"
    model_config = ConfigDict(from_attributes = True)


# Importing here to avoid circular import issues
from db.schema.user import User

Invite.model_rebuild()
