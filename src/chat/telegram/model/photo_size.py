class PhotoSize:
    """https://core.telegram.org/bots/api#photosize"""
    file_id: str
    file_unique_id: str
    width: int
    height: int
    file_size: int | None

    def __init__(
        self,
        file_id: str,
        file_unique_id: str,
        width: int,
        height: int,
        file_size: int | None = None
    ):
        self.file_id = file_id
        self.file_unique_id = file_unique_id
        self.width = width
        self.height = height
        self.file_size = file_size
