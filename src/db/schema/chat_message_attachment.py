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


class ChatMessageAttachmentCreate(ChatMessageAttachmentBase):
    pass


class ChatMessageAttachmentUpdate(ChatMessageAttachmentBase):
    pass


class ChatMessageAttachment(ChatMessageAttachmentBase):
    model_config = ConfigDict(from_attributes = True)
