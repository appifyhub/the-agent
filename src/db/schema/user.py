from datetime import date
from typing import List
from uuid import UUID

from pydantic import ConfigDict, BaseModel


class UserBase(BaseModel):
    full_name: str | None = None
    telegram_username: str | None = None
    telegram_chat_id: str | None = None
    telegram_user_id: int | None = None
    open_ai_key: str | None = None
    group: str = "standard"


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    full_name: str | None
    telegram_username: str | None
    telegram_chat_id: str | None
    telegram_user_id: int | None
    open_ai_key: str | None
    group: str


# noinspection PyUnresolvedReferences
class User(UserBase):
    id: UUID
    created_at: date
    sent_invites: List["Invite"] = []
    received_invites: List["Invite"] = []
    messages: List["ChatMessage"] = []
    model_config = ConfigDict(from_attributes = True)


# Importing here to avoid circular import issues
from db.schema.invite import Invite
from db.schema.chat_message import ChatMessage

User.model_rebuild()
