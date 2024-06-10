from pydantic import BaseModel, ConfigDict


class ChatConfigBase(BaseModel):
    chat_id: str
    persona_code: str
    persona_name: str
    language_iso_code: str = "en"
    language_name: str = "English"


class ChatConfigSave(ChatConfigBase):
    pass


class ChatConfig(ChatConfigBase):
    model_config = ConfigDict(from_attributes = True)
