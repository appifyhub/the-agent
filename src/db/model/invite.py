import uuid

from sqlalchemy import Column, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.sql import BaseModel


class Invite(BaseModel):
    __tablename__ = "invites"

    id = Column(UUID(as_uuid = True), primary_key = True, default = uuid.uuid4)
    sender_id = Column(UUID(as_uuid = True), ForeignKey("simulants.id"), nullable = False)
    receiver_id = Column(UUID(as_uuid = True), ForeignKey("simulants.id"), nullable = False)
    invited_at = Column(DateTime, default = func.now(), nullable = False)
    accepted_at = Column(DateTime, nullable = True)

    sender = relationship("User", foreign_keys = [sender_id], back_populates = "sent_invites")
    receiver = relationship("User", foreign_keys = [receiver_id], back_populates = "received_invites")
