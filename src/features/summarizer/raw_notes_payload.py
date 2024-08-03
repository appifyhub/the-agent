from pydantic import BaseModel


class RawNotesPayload(BaseModel):
    raw_notes_b64: str
