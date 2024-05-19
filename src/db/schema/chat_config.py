from pydantic import BaseModel


class ChatConfigBase(BaseModel):
    chat_id: str
    persona_code: str
    persona_name: str
    language_iso_code: str = "en"
    language_name: str = "English"


class ChatConfigCreate(ChatConfigBase):
    pass


class ChatConfigUpdate(BaseModel):
    persona_code: str
    persona_name: str
    language_iso_code: str
    language_name: str


class ChatConfig(ChatConfigBase):
    class Config:
        from_attributes = True
