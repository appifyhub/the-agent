from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from db.model.user import UserDB


class UserBase(BaseModel):
    full_name: str | None = None
    telegram_username: str | None = None
    telegram_chat_id: str | None = None
    telegram_user_id: int | None = None
    open_ai_key: str | None = None
    group: UserDB.Group = UserDB.Group.standard


class UserSave(UserBase):
    id: UUID | None = None


class User(UserBase):
    id: UUID
    created_at: date
    model_config = ConfigDict(from_attributes = True)
