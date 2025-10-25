from pydantic import BaseModel, Field


class Context(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages"""
    from_: str = Field(alias = "from")
    id: str
