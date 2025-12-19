from uuid import UUID

from pydantic import BaseModel, ConfigDict

from db.model.chat_config import ChatConfigDB


class ChatConfigBase(BaseModel):
    external_id: str | None = None
    language_iso_code: str | None = None
    language_name: str | None = None
    title: str | None = None
    is_private: bool = False
    reply_chance_percent: int = 100
    release_notifications: ChatConfigDB.ReleaseNotifications = ChatConfigDB.ReleaseNotifications.major
    media_mode: ChatConfigDB.MediaMode = ChatConfigDB.MediaMode.photo
    use_about_me: bool = True
    chat_type: ChatConfigDB.ChatType


class ChatConfigSave(ChatConfigBase):
    chat_id: UUID | None = None


class ChatConfig(ChatConfigBase):
    chat_id: UUID
    model_config = ConfigDict(from_attributes = True)
