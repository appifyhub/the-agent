from pydantic import BaseModel


class Chat(BaseModel):
    """https://core.telegram.org/bots/api#chat"""
    id: int
    type: str
    title: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
