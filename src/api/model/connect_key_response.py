from pydantic import BaseModel


class ConnectKeyResponse(BaseModel):
    connect_key: str
