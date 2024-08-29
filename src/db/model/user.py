import uuid
from datetime import date
from enum import Enum

from sqlalchemy import Column, String, Date, Enum as EnumSQL, BigInteger
from sqlalchemy.dialects.postgresql import UUID

from db.sql import BaseModel


class UserDB(BaseModel):
    __tablename__ = "simulants"

    class Group(Enum):
        standard = "standard"
        beta = "beta"
        alpha = "alpha"
        developer = "developer"

        def __lt__(self, other):
            if not isinstance(other, UserDB.Group):
                return NotImplemented
            hierarchy = {
                "standard": 1,
                "beta": 2,
                "alpha": 3,
                "developer": 4,
            }
            return hierarchy[self.value] < hierarchy[other.value]

        def __ge__(self, other):
            if not isinstance(other, UserDB.Group):
                return NotImplemented
            hierarchy = {
                "standard": 1,
                "beta": 2,
                "alpha": 3,
                "developer": 4,
            }
            return hierarchy[self.value] >= hierarchy[other.value]

    id = Column(UUID(as_uuid = True), primary_key = True, default = uuid.uuid4)
    full_name = Column(String, nullable = True)
    telegram_username = Column(String, nullable = True)  # can be changed in Telegram
    telegram_chat_id = Column(String, nullable = True)  # can be changed in Telegram
    telegram_user_id = Column(BigInteger, unique = True, nullable = True, index = True)
    open_ai_key = Column(String, nullable = True)
    group = Column(EnumSQL(Group), nullable = False, default = Group.standard)
    created_at = Column(Date, default = date.today)

    __table_args__ = ()
