from dataclasses import dataclass
from uuid import UUID


@dataclass
class ParticipantInfo:
    user_id: UUID
    full_name: str | None
    platform: str | None
    handle: str | None


@dataclass
class ParticipantDetails:
    payer: ParticipantInfo
    owner: ParticipantInfo
    counterpart: ParticipantInfo | None = None
