import uuid
from enum import Enum

from sqlalchemy import Boolean, Column, Index, Integer, String
from sqlalchemy import Enum as EnumSQL
from sqlalchemy.dialects.postgresql import UUID

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

    class ChatType(Enum):
        standalone_web = "standalone_web"
        standalone_app = "standalone_app"
        extension_web = "extension_web"
        telegram = "telegram"
        whatsapp = "whatsapp"

        @classmethod
        def lookup(cls, value) -> "ChatConfigDB.ChatType | None":
            try:
                return cls(value)
            except ValueError:
                return None

        def __lt__(self, other):
            if not isinstance(other, ChatConfigDB.ChatType):
                return NotImplemented
            hierarchy = {
                "standalone_web": 1,
                "standalone_app": 2,
                "extension_web": 3,
                "telegram": 4,
                "whatsapp": 5,
            }
            return hierarchy[self.value] < hierarchy[other.value]

        def __ge__(self, other):
            if not isinstance(other, ChatConfigDB.ChatType):
                return NotImplemented
            hierarchy = {
                "standalone_web": 1,
                "standalone_app": 2,
                "extension_web": 3,
                "telegram": 4,
                "whatsapp": 5,
            }
            return hierarchy[self.value] >= hierarchy[other.value]

    chat_id = Column(UUID(as_uuid = True), primary_key = True, default = uuid.uuid4)
    external_id = Column(String, nullable = True)
    language_iso_code = Column(String, nullable = True)
    language_name = Column(String, nullable = True)
    title = Column(String, nullable = True)
    is_private = Column(Boolean, nullable = False)
    reply_chance_percent = Column(Integer, nullable = False)
    release_notifications = Column(EnumSQL(ReleaseNotifications), nullable = False, default = ReleaseNotifications.all)
    chat_type = Column(EnumSQL(ChatType), nullable = False)

    __table_args__ = (
        Index(
            "uq_chat_configs_external_id_type",
            external_id,
            chat_type,
            unique = True,
            postgresql_where = external_id.isnot(None),
        ),
    )
