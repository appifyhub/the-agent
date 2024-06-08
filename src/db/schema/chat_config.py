from pydantic import BaseModel, ConfigDict


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
    model_config = ConfigDict(from_attributes = True)
