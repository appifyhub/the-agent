from enum import Enum

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy import Enum as EnumSQL

from db.model.base import BaseModel


class ChatConfigDB(BaseModel):
    __tablename__ = "chat_configs"

    class ReleaseNotifications(Enum):
        none = "none"
        major = "major"
        minor = "minor"
        all = "all"

        @classmethod
        def lookup(cls, value) -> "ChatConfigDB.ReleaseNotifications | None":
            try:
                return cls(value)
            except ValueError:
                return None

        def __lt__(self, other):
            if not isinstance(other, ChatConfigDB.ReleaseNotifications):
                return NotImplemented
            hierarchy = {
                "none": 1,
                "major": 2,
                "minor": 3,
                "all": 4,
            }
            return hierarchy[self.value] < hierarchy[other.value]

        def __ge__(self, other):
            if not isinstance(other, ChatConfigDB.ReleaseNotifications):
                return NotImplemented
            hierarchy = {
                "none": 1,
                "major": 2,
                "minor": 3,
                "all": 4,
            }
            return hierarchy[self.value] >= hierarchy[other.value]

    chat_id = Column(String, primary_key = True)
    language_iso_code = Column(String, nullable = True)
    language_name = Column(String, nullable = True)
    title = Column(String, nullable = True)
    is_private = Column(Boolean, nullable = False)
    reply_chance_percent = Column(Integer, nullable = False)
    release_notifications = Column(EnumSQL(ReleaseNotifications), nullable = False, default = ReleaseNotifications.all)
