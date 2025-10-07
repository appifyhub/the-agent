from pydantic import BaseModel

from features.chat.whatsapp.model.entry import Entry


class Update(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages"""
    object: str
    entry: list[Entry]
