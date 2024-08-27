from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChatMessageAttachmentBase(BaseModel):
    id: str
    chat_id: str
    message_id: str
    size: int | None = None
    last_url: str | None = None
    last_url_until: int | None = None
    extension: str | None = None
    mime_type: str | None = None

    @property
    def has_stale_data(self) -> bool:
        is_missing_url = not self.last_url
        expiration_timestamp = self.last_url_until or 0
        is_url_expired = expiration_timestamp <= int(datetime.now().timestamp())
        return is_missing_url or is_url_expired


class ChatMessageAttachmentSave(ChatMessageAttachmentBase):
    pass


class ChatMessageAttachment(ChatMessageAttachmentBase):
    model_config = ConfigDict(from_attributes = True)
