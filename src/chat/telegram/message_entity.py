from chat.telegram.user import User


class MessageEntity:
    """https://core.telegram.org/bots/api#messageentity"""
    type: str
    offset: int
    length: int
    url: str | None
    user: User | None
    language: str | None  # programming language of the code block

    def __init__(
        self,
        type: str,
        offset: int,
        length: int,
        url: str | None = None,
        user: User | None = None,
        language: str | None = None,
    ):
        self.type = type
        self.offset = offset
        self.length = length
        self.url = url
        self.user = user
        self.language = language
