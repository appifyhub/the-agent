from pydantic import BaseModel


class Text(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#text-messages"""
    body: str
