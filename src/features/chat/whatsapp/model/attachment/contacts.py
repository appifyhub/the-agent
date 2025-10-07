from pydantic import BaseModel


class ContactName(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#contacts-messages"""
    formatted_name: str
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    suffix: str | None = None
    prefix: str | None = None


class ContactPhone(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#contacts-messages"""
    phone: str
    type: str | None = None
    wa_id: str | None = None


class ContactEmail(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#contacts-messages"""
    email: str
    type: str | None = None


class ContactUrl(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#contacts-messages"""
    url: str
    type: str | None = None


class ContactAddress(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#contacts-messages"""
    street: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    country: str | None = None
    country_code: str | None = None
    type: str | None = None


class ContactOrg(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#contacts-messages"""
    company: str | None = None
    department: str | None = None
    title: str | None = None


class ContactCard(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#contacts-messages"""
    name: ContactName
    phones: list[ContactPhone] | None = None
    emails: list[ContactEmail] | None = None
    urls: list[ContactUrl] | None = None
    addresses: list[ContactAddress] | None = None
    org: ContactOrg | None = None
    birthday: str | None = None


class Contacts(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#contacts-messages"""
    contacts: list[ContactCard]
