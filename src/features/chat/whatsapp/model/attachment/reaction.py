from pydantic import BaseModel


class Reaction(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#reaction-messages"""
    message_id: str
    emoji: str
