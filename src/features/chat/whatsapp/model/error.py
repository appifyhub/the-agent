from pydantic import BaseModel


class Error(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#errors"""
    code: int
    title: str
    message: str | None = None
    error_data: dict | None = None
