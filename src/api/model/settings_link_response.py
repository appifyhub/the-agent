from pydantic import BaseModel


class SettingsLinkResponse(BaseModel):
    settings_link: str
