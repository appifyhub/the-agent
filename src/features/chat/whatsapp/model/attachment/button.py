from pydantic import BaseModel


class Button(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#button-messages"""
    payload: str
    text: str
