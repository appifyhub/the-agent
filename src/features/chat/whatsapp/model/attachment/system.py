from pydantic import BaseModel


class System(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#system-messages"""
    body: str
    type: str
    new_wa_id: str | None = None
    customer: str | None = None
