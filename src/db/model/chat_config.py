from sqlalchemy import Column, String, Boolean, Integer

from db.model.base import BaseModel


class ChatConfigDB(BaseModel):
    __tablename__ = "chat_configs"

    chat_id = Column(String, primary_key = True)
    language_iso_code = Column(String, nullable = True)
    language_name = Column(String, nullable = True)
    title = Column(String, nullable = True)
    is_private = Column(Boolean, nullable = False)
    reply_chance_percent = Column(Integer, nullable = False)
