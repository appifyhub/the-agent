from chat.telegram.photo_size import PhotoSize


class Document:
    """https://core.telegram.org/bots/api#document"""
    file_id: str
    file_unique_id: str
    thumbnail: PhotoSize | None
    file_name: str | None
    mime_type: str | None
    file_size: int | None

    def __init__(
        self,
        file_id: str,
        file_unique_id: str,
        thumbnail: PhotoSize | None = None,
        file_name: str | None = None,
        mime_type: str | None = None,
        file_size: int | None = None
    ):
        self.file_id = file_id
        self.file_unique_id = file_unique_id
        self.thumbnail = thumbnail
        self.file_name = file_name
        self.mime_type = mime_type
        self.file_size = file_size
