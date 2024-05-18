from pydantic import BaseModel


class ChatConfigBase(BaseModel):
    persona_code: str
    persona_name: str
    language_iso_code: str = "en"
    language_name: str = "English"


class ChatConfigCreate(ChatConfigBase):
    pass


class ChatConfig(ChatConfigBase):
    chat_id: str

    class Config:
        orm_mode = True
