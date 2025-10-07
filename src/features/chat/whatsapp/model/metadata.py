from pydantic import BaseModel


class Metadata(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#metadata-object"""
    display_phone_number: str
    phone_number_id: str
