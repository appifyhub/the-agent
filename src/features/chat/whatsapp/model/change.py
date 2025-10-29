from pydantic import BaseModel

from features.chat.whatsapp.model.value import Value


class Change(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages"""
    value: Value
    field: str
