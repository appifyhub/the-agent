from pydantic import BaseModel

from features.chat.whatsapp.model.error import Error


class Unsupported(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#unsupported-messages"""
    errors: list[Error]
