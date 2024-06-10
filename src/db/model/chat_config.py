from sqlalchemy import Column, String

from db.sql import BaseModel


class ChatConfigDB(BaseModel):
    __tablename__ = "chat_configs"

    chat_id = Column(String, primary_key = True)
    persona_code = Column(String, nullable = True)
    persona_name = Column(String, nullable = True)
    language_iso_code = Column(String, nullable = True)
    language_name = Column(String, nullable = True)
