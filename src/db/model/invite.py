from sqlalchemy import Column, ForeignKey, DateTime, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from db.model.base import BaseModel


class InviteDB(BaseModel):
    __tablename__ = "invites"

    sender_id = Column(UUID(as_uuid = True), ForeignKey("simulants.id"), nullable = False)
    receiver_id = Column(UUID(as_uuid = True), ForeignKey("simulants.id"), nullable = False)
    invited_at = Column(DateTime, default = func.now(), nullable = False)
    accepted_at = Column(DateTime, nullable = True)

    __table_args__ = (
        PrimaryKeyConstraint(sender_id, receiver_id),
    )
