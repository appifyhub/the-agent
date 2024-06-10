from pydantic import BaseModel, ConfigDict


class ChatConfigBase(BaseModel):
    chat_id: str
    persona_code: str | None = None
    persona_name: str | None = None
    language_iso_code: str | None = None
    language_name: str | None = None


class ChatConfigSave(ChatConfigBase):
    pass


class ChatConfig(ChatConfigBase):
    model_config = ConfigDict(from_attributes = True)
