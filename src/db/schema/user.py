from datetime import date
from typing import List
from uuid import UUID

from pydantic import BaseModel


class UserBase(BaseModel):
    full_name: str | None = None
    telegram_username: str | None = None
    telegram_chat_id: str | None = None
    open_ai_key: str | None = None
    group: str = "standard"


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    full_name: str | None
    telegram_username: str | None
    telegram_chat_id: str | None
    open_ai_key: str | None
    group: str


# noinspection PyUnresolvedReferences
class User(UserBase):
    id: UUID
    created_at: date
    sent_invites: List["Invite"] = []
    received_invites: List["Invite"] = []

    class Config:
        from_attributes = True


# Importing here to avoid circular import issues
from db.schema.invite import Invite

User.model_rebuild()
