from typing import Literal

from pydantic import BaseModel


class ListReply(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#interactive-messages"""
    id: str
    title: str
    description: str | None = None


class ButtonReply(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#interactive-messages"""
    id: str
    title: str


class NfmReply(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#interactive-messages"""
    name: str
    body: str


class Interactive(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#interactive-messages"""
    type: Literal["list_reply", "button_reply", "nfm_reply"]
    list_reply: ListReply | None = None
    button_reply: ButtonReply | None = None
    nfm_reply: NfmReply | None = None
