from datetime import date
from typing import List
from uuid import UUID

from pydantic import BaseModel

from db.schema.invite import Invite


class UserBase(BaseModel):
    full_name: str | None = None
    telegram_username: str | None = None
    telegram_chat_id: str | None = None
    open_ai_key: str | None = None
    group: str = "standard"


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: UUID
    created_at: date
    sent_invites: List[Invite] = []
    received_invites: List[Invite] = []

    class Config:
        orm_mode = True
