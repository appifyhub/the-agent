from pydantic import BaseModel, ConfigDict

from db.model.chat_config import ChatConfigDB


class ChatConfigBase(BaseModel):
    chat_id: str
    language_iso_code: str | None = None
    language_name: str | None = None
    title: str | None = None
    is_private: bool = False
    reply_chance_percent: int = 100
    release_notifications: ChatConfigDB.ReleaseNotifications = ChatConfigDB.ReleaseNotifications.all
    chat_type: ChatConfigDB.ChatType


class ChatConfigSave(ChatConfigBase):
    pass


class ChatConfig(ChatConfigBase):
    model_config = ConfigDict(from_attributes = True)
