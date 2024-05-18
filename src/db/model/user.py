import enum
import uuid
from datetime import date

from sqlalchemy import Column, String, Date, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db.model.invite import Invite
from db.sql import BaseModel


class User(BaseModel):
    __tablename__ = 'simulants'

    class Group(enum.Enum):
        standard = "standard"
        beta = "beta"
        alpha = "alpha"
        developer = "developer"

    id = Column(UUID(as_uuid = True), primary_key = True, default = uuid.uuid4)
    full_name = Column(String, nullable = True)
    telegram_username = Column(String, unique = True, nullable = True, index = True)
    telegram_chat_id = Column(String, unique = True, nullable = True, index = True)
    open_ai_key = Column(String, nullable = True)
    group = Column(Enum(Group), nullable = False, default = Group.standard)
    created_at = Column(Date, default = date.today)

    sent_invites = relationship("Invite", foreign_keys = [Invite.sender_id], back_populates = "sender")
    received_invites = relationship("Invite", foreign_keys = [Invite.receiver_id], back_populates = "receiver")
