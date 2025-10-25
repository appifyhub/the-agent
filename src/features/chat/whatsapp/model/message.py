
from typing import Literal

from pydantic import BaseModel, Field

from features.chat.whatsapp.model.attachment.media_attachment import MediaAttachment
from features.chat.whatsapp.model.attachment.text import Text
from features.chat.whatsapp.model.context import Context


class Message(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages"""
    from_: str = Field(alias = "from")
    id: str
    timestamp: str
    type: Literal[
        "text", "image", "video", "audio", "document",
        "sticker", "location", "contacts",
        "interactive", "button", "reaction",
        "order", "system", "unsupported",
    ]
    text: Text | None = None
    image: MediaAttachment | None = None
    video: MediaAttachment | None = None
    audio: MediaAttachment | None = None
    document: MediaAttachment | None = None
    sticker: MediaAttachment | None = None
    location: dict | None = None
    contacts: dict | None = None
    interactive: dict | None = None
    button: dict | None = None
    reaction: dict | None = None
    order: dict | None = None
    system: dict | None = None
    context: Context | None = None
