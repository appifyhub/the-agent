from pydantic import BaseModel


class ChatSettingsResponse(BaseModel):
    chat_id: str
    title: str | None = None
    platform: str
    language_name: str | None = None
    language_iso_code: str | None = None
    reply_chance_percent: int
    release_notifications: str
    is_private: bool
    is_own: bool
