class Chat:
    """https://core.telegram.org/bots/api#chat"""
    id: int
    type: str
    title: str | None
    username: str | None
    first_name: str | None
    last_name: str | None

    def __init__(
        self,
        id: int,
        type: str,
        title: str | None = None,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ):
        self.id = id
        self.type = type
        self.title = title
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
