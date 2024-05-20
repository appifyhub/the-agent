from sqlalchemy import Column, ForeignKey, DateTime, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.sql import BaseModel


class InviteDB(BaseModel):
    __tablename__ = "invites"

    sender_id = Column(UUID(as_uuid = True), ForeignKey("simulants.id"), nullable = False)
    receiver_id = Column(UUID(as_uuid = True), ForeignKey("simulants.id"), nullable = False)
    invited_at = Column(DateTime, default = func.now(), nullable = False)
    accepted_at = Column(DateTime, nullable = True)

    sender = relationship("UserDB", foreign_keys = [sender_id], back_populates = "sent_invites")
    receiver = relationship("UserDB", foreign_keys = [receiver_id], back_populates = "received_invites")

    __table_args__ = (
        PrimaryKeyConstraint(sender_id, receiver_id),
    )
