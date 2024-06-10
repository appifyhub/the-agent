from datetime import datetime, timedelta
from typing import List

from chat.telegram.bot_api import BotAPI
from chat.telegram.model.attachment.file import File
from chat.telegram.model.chat import Chat
from chat.telegram.model.message import Message
from db.schema.chat_config import ChatConfigSave
from db.schema.chat_message_attachment import ChatMessageAttachmentSave
from util.safe_printer_mixin import SafePrinterMixin

# Based on popularity and support in vision models
SUPPORTED_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
}


class Converter(SafePrinterMixin):
    __api: BotAPI

    def __init__(self, config):
        super().__init__(config.verbose)
        self.__api = BotAPI(config)

    def __convert_chat(self, chat: Chat) -> ChatConfigSave:
        self.sprint(f"Converting chat: {chat}")
        title = self.__resolve_chat_name(str(chat.id), chat.title, chat.username, chat.first_name, chat.last_name)
        return ChatConfigSave(
            chat_id = str(chat.id),
            title = title,
            is_private = chat.type == "private",
        )

    def __resolve_chat_name(
        self,
        chat_id: str,
        title: str | None = None,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> str:
        parts = []
        if title:
            parts.append(title)
        if username:
            parts.append(f"@{username}")
        if first_name or last_name:
            owner_parts = []
            if first_name:
                owner_parts.append(first_name)
            if last_name:
                owner_parts.append(last_name)
            parts.append(" ".join(owner_parts))
        result = " · ".join(parts) if parts else f"#{chat_id}"
        self.sprint(f"Resolved chat name {result}")
        return result

    def __convert_attachments(self, message: Message) -> List[ChatMessageAttachmentSave]:
        attachments: List[ChatMessageAttachmentSave] = []
        if message.audio:
            self.sprint(f"Converting audio: {message.audio}")
            attachments.append(
                self.__convert_to_attachment(
                    self.__api.get_file_info(message.audio.file_id),
                    str(message.chat.id),
                    str(message.message_id),
                    message.audio.mime_type,
                )
            )
        if message.document:
            self.sprint(f"Converting document: {message.document}")
            attachments.append(
                self.__convert_to_attachment(
                    self.__api.get_file_info(message.document.file_id),
                    str(message.chat.id),
                    str(message.message_id),
                    message.document.mime_type,
                )
            )
        if message.photo:
            largest_photo = max(message.photo, key = lambda size: size.width * size.height)
            self.sprint(f"Converting photo: {largest_photo}")
            attachments.append(
                self.__convert_to_attachment(
                    self.__api.get_file_info(largest_photo.file_id),
                    str(message.chat.id),
                    str(message.message_id),
                )
            )
        if message.voice:
            self.sprint(f"Converting voice: {message.voice}")
            attachments.append(
                self.__convert_to_attachment(
                    self.__api.get_file_info(message.voice.file_id),
                    str(message.chat.id),
                    str(message.message_id),
                    message.voice.mime_type,
                )
            )
        return attachments

    def __convert_to_attachment(
        self,
        file: File,
        chat_id: str,
        message_id: str,
        mime_type: str | None = None,
    ) -> ChatMessageAttachmentSave:
        self.sprint(f"Creating attachment from file: {file}")
        extension: str | None = None
        if file.file_path and ("." in file.file_path):
            extension = file.file_path.split(".")[-1]
        if not mime_type:
            mime_type = SUPPORTED_MIME_TYPES.get(extension, None)
        self.sprint(f"Resolved:\n\textension '.{extension}'\n\tmime-type '{mime_type}'")
        return ChatMessageAttachmentSave(
            id = file.file_id,
            chat_id = chat_id,
            message_id = message_id,
            size = file.file_size,
            last_url = file.file_path,
            last_url_until = self.__nearest_hour_epoch(),
            extension = extension,
            mime_type = mime_type,
        )

    def __nearest_hour_epoch(self) -> int:
        last_hour_mark: datetime = datetime.now().replace(minute = 0, second = 0, microsecond = 0)
        next_hour_mark: datetime = last_hour_mark + timedelta(hours = 1)
        self.sprint(f"Last hour mark: {next_hour_mark}")
        return int(next_hour_mark.timestamp())
