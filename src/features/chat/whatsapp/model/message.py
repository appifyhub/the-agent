from typing import Literal

from pydantic import BaseModel, Field

from features.chat.whatsapp.model.attachment.audio import Audio
from features.chat.whatsapp.model.attachment.button import Button
from features.chat.whatsapp.model.attachment.contacts import Contacts
from features.chat.whatsapp.model.attachment.document import Document
from features.chat.whatsapp.model.attachment.image import Image
from features.chat.whatsapp.model.attachment.interactive import Interactive
from features.chat.whatsapp.model.attachment.location import Location
from features.chat.whatsapp.model.attachment.order import Order
from features.chat.whatsapp.model.attachment.reaction import Reaction
from features.chat.whatsapp.model.attachment.sticker import Sticker
from features.chat.whatsapp.model.attachment.system import System
from features.chat.whatsapp.model.attachment.text import Text
from features.chat.whatsapp.model.attachment.unsupported import Unsupported
from features.chat.whatsapp.model.attachment.video import Video
from features.chat.whatsapp.model.context import Context
from features.chat.whatsapp.model.error import Error


class Message(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages"""
    id: str
    from_: str = Field(alias = "from")
    timestamp: str
    type: Literal[
        "text", "image", "video", "audio", "document", "sticker", "location", "contacts",
        "button", "interactive", "reaction", "order", "system", "unsupported",
    ]
    context: Context | None = None
    text: Text | None = None
    image: Image | None = None
    video: Video | None = None
    audio: Audio | None = None
    document: Document | None = None
    sticker: Sticker | None = None
    location: Location | None = None
    contacts: Contacts | None = None
    button: Button | None = None
    interactive: Interactive | None = None
    reaction: Reaction | None = None
    order: Order | None = None
    system: System | None = None
    unsupported: Unsupported | None = None
    errors: list[Error] | None = None
