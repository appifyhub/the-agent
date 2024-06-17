from pydantic import BaseModel

from features.chat.telegram.model.message import Message


class Update(BaseModel):
    """https://core.telegram.org/bots/api#update"""
    update_id: int
    message: Message | None = None
    edited_message: Message | None = None
