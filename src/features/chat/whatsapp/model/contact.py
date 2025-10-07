from pydantic import BaseModel

from features.chat.whatsapp.model.profile import Profile


class Contact(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#contacts-object"""
    profile: Profile
    wa_id: str
