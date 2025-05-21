from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SponsorshipBase(BaseModel):
    sponsor_id: UUID
    receiver_id: UUID


class SponsorshipSave(SponsorshipBase):
    accepted_at: datetime | None = None


class Sponsorship(SponsorshipBase):
    sponsored_at: datetime
    accepted_at: datetime | None
    model_config = ConfigDict(from_attributes = True)
