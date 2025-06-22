import uuid
from datetime import date
from enum import Enum

from sqlalchemy import BigInteger, Column, Date, String
from sqlalchemy import Enum as EnumSQL
from sqlalchemy.dialects.postgresql import UUID

from db.model.base import BaseModel


class UserDB(BaseModel):
    __tablename__ = "simulants"

    class Group(Enum):
        standard = "standard"
        developer = "developer"

        def __lt__(self, other):
            if not isinstance(other, UserDB.Group):
                return NotImplemented
            hierarchy = {
                "standard": 1,
                "developer": 2,
            }
            return hierarchy[self.value] < hierarchy[other.value]

        def __ge__(self, other):
            if not isinstance(other, UserDB.Group):
                return NotImplemented
            hierarchy = {
                "standard": 1,
                "developer": 2,
            }
            return hierarchy[self.value] >= hierarchy[other.value]

    id = Column(UUID(as_uuid = True), primary_key = True, default = uuid.uuid4)
    full_name = Column(String, nullable = True)
    telegram_username = Column(String, nullable = True)  # can be changed in Telegram
    telegram_chat_id = Column(String, nullable = True)  # can be changed in Telegram
    telegram_user_id = Column(BigInteger, unique = True, nullable = True, index = True)
    open_ai_key = Column(String, nullable = True)
    anthropic_key = Column(String, nullable = True)
    perplexity_key = Column(String, nullable = True)
    replicate_key = Column(String, nullable = True)
    rapid_api_key = Column(String, nullable = True)
    coinmarketcap_key = Column(String, nullable = True)
    group = Column(EnumSQL(Group), nullable = False, default = Group.standard)
    created_at = Column(Date, default = date.today)

    __table_args__ = ()
