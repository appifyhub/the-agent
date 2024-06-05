class User:
    """https://core.telegram.org/bots/api#messageentity"""
    id: int
    is_bot: bool
    first_name: str
    last_name: str | None
    username: str | None
    language_code: str | None  # IETF language tag

    def __init__(
        self,
        id: int,
        is_bot: bool,
        first_name: str,
        last_name: str | None = None,
        username: str | None = None,
        language_code: str | None = None,
    ):
        self.id = id
        self.is_bot = is_bot
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.language_code = language_code
