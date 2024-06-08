from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class InviteBase(BaseModel):
    sender_id: UUID
    receiver_id: UUID


class InviteCreate(InviteBase):
    pass


class InviteUpdate(BaseModel):
    accepted_at: datetime | None


class Invite(InviteBase):
    invited_at: datetime
    accepted_at: datetime | None = None
    model_config = ConfigDict(from_attributes = True)
