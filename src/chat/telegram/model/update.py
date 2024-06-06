from chat.telegram.model.message import Message


class Update:
    """https://core.telegram.org/bots/api#update"""
    update_id: int
    message: Message | None
    edited_message: Message | None

    def __init__(
        self,
        update_id: int,
        message: Message | None = None,
        edited_message: Message | None = None
    ):
        self.update_id = update_id
        self.message = message
        self.edited_message = edited_message
