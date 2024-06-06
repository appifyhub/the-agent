from chat.telegram.model.photo_size import PhotoSize


class Audio:
    """https://core.telegram.org/bots/api#audio"""
    file_id: str
    file_unique_id: str
    duration: int
    performer: str | None
    title: str | None
    file_name: str | None
    mime_type: str | None
    file_size: int | None
    thumbnail: PhotoSize | None

    def __init__(
        self,
        file_id: str,
        file_unique_id: str,
        duration: int,
        performer: str | None = None,
        title: str | None = None,
        file_name: str | None = None,
        mime_type: str | None = None,
        file_size: int | None = None,
        thumbnail: PhotoSize | None = None
    ):
        self.file_id = file_id
        self.file_unique_id = file_unique_id
        self.duration = duration
        self.performer = performer
        self.title = title
        self.file_name = file_name
        self.mime_type = mime_type
        self.file_size = file_size
        self.thumbnail = thumbnail
