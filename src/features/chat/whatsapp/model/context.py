from pydantic import BaseModel, Field


class Context(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages"""
    from_: str | None = Field(default = None, alias = "from")
    id: str | None = None
