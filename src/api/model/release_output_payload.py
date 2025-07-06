from pydantic import BaseModel


class ReleaseOutputPayload(BaseModel):
    release_output_b64: str
