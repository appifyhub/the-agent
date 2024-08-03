from pydantic import BaseModel


class RawNotesPayload(BaseModel):
    raw_notes: str
