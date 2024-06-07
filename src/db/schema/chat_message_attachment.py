from pydantic import ConfigDict, BaseModel


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


class ChatMessageAttachmentUpdate(BaseModel):
    size: int | None = None
    last_url: str | None = None
    last_url_until: int | None = None
    extension: str | None = None
    mime_type: str | None = None


class ChatMessageAttachment(ChatMessageAttachmentBase):
    model_config = ConfigDict(from_attributes = True)
