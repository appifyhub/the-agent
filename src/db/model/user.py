import enum
import uuid
from datetime import date

from sqlalchemy import Column, String, Date, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID

from db.sql import BaseModel


class UserDB(BaseModel):
    __tablename__ = "simulants"

    class Group(enum.Enum):
        standard = "standard"
        beta = "beta"
        alpha = "alpha"
        developer = "developer"

    id = Column(UUID(as_uuid = True), primary_key = True, default = uuid.uuid4)
    full_name = Column(String, nullable = True)
    telegram_username = Column(String, nullable = True)  # can be changed in Telegram
    telegram_chat_id = Column(String, nullable = True)  # can be changed in Telegram
    telegram_user_id = Column(Integer, unique = True, nullable = True, index = True)
    open_ai_key = Column(String, nullable = True)
    group = Column(Enum(Group), nullable = False, default = Group.standard)
    created_at = Column(Date, default = date.today)

    __table_args__ = ()
