class Voice:
    """https://core.telegram.org/bots/api#voice"""
    file_id: str
    file_unique_id: str
    duration: int
    mime_type: str | None
    file_size: int | None

    def __init__(
        self,
        file_id: str,
        file_unique_id: str,
        duration: int,
        mime_type: str | None = None,
        file_size: int | None = None
    ):
        self.file_id = file_id
        self.file_unique_id = file_unique_id
        self.duration = duration
        self.mime_type = mime_type
        self.file_size = file_size
