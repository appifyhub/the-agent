from pydantic import BaseModel


class User(BaseModel):
    """https://core.telegram.org/bots/api#user"""
    id: int
    is_bot: bool
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
