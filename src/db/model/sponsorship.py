from sqlalchemy import Column, DateTime, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from db.model.base import BaseModel


class SponsorshipDB(BaseModel):
    __tablename__ = "sponsorships"

    sponsor_id = Column(UUID(as_uuid = True), ForeignKey("simulants.id"), nullable = False)
    receiver_id = Column(UUID(as_uuid = True), ForeignKey("simulants.id"), nullable = False)
    sponsored_at = Column(DateTime, default = func.now(), nullable = False)
    accepted_at = Column(DateTime, nullable = True)

    __table_args__ = (
        PrimaryKeyConstraint(sponsor_id, receiver_id),
    )
