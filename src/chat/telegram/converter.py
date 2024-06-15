from datetime import datetime, timedelta
from typing import List

from chat.telegram.model.attachment.file import File
from chat.telegram.model.message import Message
from chat.telegram.model.update import Update
from db.model.user import UserDB
from db.schema.chat_config import ChatConfigSave
from db.schema.chat_message import ChatMessageSave
from db.schema.chat_message_attachment import ChatMessageAttachmentSave
from db.schema.user import UserSave
from util.config import Config
from util.safe_printer_mixin import SafePrinterMixin

# Based on popularity and support in vision models
SUPPORTED_MIME_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "bmp": "image/bmp",
    "tiff": "image/tiff",
    "tif": "image/tiff",
}


class ConversionResult:
    chat: ChatConfigSave
    author: UserSave | None
    message: ChatMessageSave
    attachments: List[ChatMessageAttachmentSave]

    def __init__(
        self,
        chat: ChatConfigSave,
        author: UserSave | None,
        message: ChatMessageSave,
        attachments: List[ChatMessageAttachmentSave],
    ):
        self.chat = chat
        self.author = author
        self.message = message
        self.attachments = attachments


class Converter(SafePrinterMixin):

    def __init__(self, config: Config):
        super().__init__(config.verbose)

    def convert_update(self, update: Update) -> ConversionResult | None:
        self.sprint(f"Converting update: {update}")
        message = update.edited_message or update.message
        if not message:
            self.sprint(f"Nothing to convert in update: {update}")
            return None
        result_chat = self.convert_chat(message)
        result_author = self.convert_author(message)
        result_message = self.convert_message(message)
        result_attachments = self.convert_attachments(message)
        return ConversionResult(
            chat = result_chat,
            author = result_author,
            message = result_message,
            attachments = result_attachments,
        )

    def convert_message(self, message: Message) -> ChatMessageSave:
        self.sprint(f"Converting message: {message}")
        return ChatMessageSave(
            chat_id = str(message.chat.id),
            message_id = str(message.message_id),
            author_id = None,  # explicitly not setting for now, it will be set after storing
            sent_at = datetime.fromtimestamp(message.edit_date or message.date),
            text = self.convert_text(message),
        )

    def convert_author(self, message: Message) -> UserSave | None:
        if not message.from_user: return None
        self.sprint(f"Converting author {message.from_user}")
        # properties might be updated later when this is stored
        author = message.from_user
        return UserSave(
            full_name = f"{author.first_name} {author.last_name}" if author.last_name else author.first_name,
            telegram_username = author.username,
            telegram_chat_id = str(message.chat.id) if message.chat.type == "private" else None,
            telegram_user_id = author.id,
            open_ai_key = None,
            group = UserDB.Group.standard,
        )

    def convert_text_as_reply(self, message: Message) -> str:
        parts = []
        if message.caption:
            parts.append(f">>>> {message.caption}")
        if message.text:
            parts.append(f">>>> {message.text}")
        attachments_as_text = self.convert_attachments_as_text(message)
        if attachments_as_text:
            parts.append(f">>>> 📎 {attachments_as_text}")
        self.sprint(f"Converting reply message text: {parts}")
        return "\n\n".join(parts)

    def convert_text(self, message: Message) -> str:
        parts = []
        reply_text = self.convert_text_as_reply(message.reply_to_message) if message.reply_to_message else None
        if reply_text:
            parts.append(f"{reply_text}")
        quote = message.quote.text if message.quote else None
        if quote:
            parts.append(f">> {quote}")
        if message.caption:
            parts.append(f"{message.caption}")
        if message.text:
            parts.append(message.text)
        attachments_as_text = self.convert_attachments_as_text(message)
        if attachments_as_text:
            parts.append(f"📎 {attachments_as_text}")
        self.sprint(f"Converting message text: {parts}")
        return "\n\n".join(parts)

    def convert_chat(self, message: Message) -> ChatConfigSave:
        chat = message.chat
        self.sprint(f"Converting chat: {chat}")
        title = self.resolve_chat_name(str(chat.id), chat.title, chat.username, chat.first_name, chat.last_name)
        return ChatConfigSave(
            chat_id = str(chat.id),
            title = title,
            is_private = chat.type == "private",
        )

    def resolve_chat_name(
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
        if first_name or last_name:
            owner_parts = []
            if first_name:
                owner_parts.append(first_name)
            if last_name:
                owner_parts.append(last_name)
            parts.append(" ".join(owner_parts))
        if username:
            parts.append(f"@{username}")
        result = " · ".join(parts) if parts else f"#{chat_id}"
        self.sprint(f"Resolved chat name {result}")
        return result

    def convert_attachments_as_text(self, message: Message) -> str | None:
        attachments = self.convert_attachments(message)
        if not attachments: return None
        formatted_attachments = [
            f"{attachment.id} ({attachment.mime_type})" if attachment.mime_type else f"{attachment.id}"
            for attachment in attachments
        ]
        self.sprint(f"Converting attachments: {formatted_attachments}")
        return f"[ {', '.join(formatted_attachments)} ]"

    def convert_attachments(self, message: Message) -> List[ChatMessageAttachmentSave]:
        attachments: List[ChatMessageAttachmentSave] = []
        if message.audio:
            self.sprint(f"Converting audio: {message.audio}")
            dummy_file = File(
                file_id = message.audio.file_id,
                file_unique_id = message.audio.file_unique_id,
                file_size = message.audio.file_size,
                file_path = None,
            )
            attachments.append(
                self.convert_to_attachment(
                    file = dummy_file,
                    chat_id = str(message.chat.id),
                    message_id = str(message.message_id),
                    mime_type = message.audio.mime_type,
                )
            )
        if message.document:
            self.sprint(f"Converting document: {message.document}")
            dummy_file = File(
                file_id = message.document.file_id,
                file_unique_id = message.document.file_unique_id,
                file_size = message.document.file_size,
                file_path = None,
            )
            attachments.append(
                self.convert_to_attachment(
                    file = dummy_file,
                    chat_id = str(message.chat.id),
                    message_id = str(message.message_id),
                    mime_type = message.document.mime_type,
                )
            )
        if message.photo:
            largest_photo = max(message.photo, key = lambda size: size.width * size.height)
            self.sprint(f"Converting photo: {largest_photo}")
            dummy_file = File(
                file_id = largest_photo.file_id,
                file_unique_id = largest_photo.file_unique_id,
                file_size = largest_photo.file_size,
                file_path = None,
            )
            attachments.append(
                self.convert_to_attachment(
                    file = dummy_file,
                    chat_id = str(message.chat.id),
                    message_id = str(message.message_id),
                )
            )
        if message.voice:
            self.sprint(f"Converting voice: {message.voice}")
            dummy_file = File(
                file_id = message.voice.file_id,
                file_unique_id = message.voice.file_unique_id,
                file_size = message.voice.file_size,
                file_path = None,
            )
            attachments.append(
                self.convert_to_attachment(
                    file = dummy_file,
                    chat_id = str(message.chat.id),
                    message_id = str(message.message_id),
                    mime_type = message.voice.mime_type,
                )
            )
        return attachments

    def convert_to_attachment(
        self,
        file: File,
        chat_id: str,
        message_id: str,
        mime_type: str | None = None,
    ) -> ChatMessageAttachmentSave:
        self.sprint(f"Creating attachment from file: {file}")
        extension: str | None = None
        last_url_until: int | None = None
        if file.file_path and ("." in file.file_path):
            extension = file.file_path.lower().split(".")[-1]
            last_url_until = self.nearest_hour_epoch()
            if not mime_type:
                mime_type = SUPPORTED_MIME_TYPES.get(extension, None)
        self.sprint(f"Resolved:\n\textension '.{extension}'\n\tmime-type '{mime_type}'")
        return ChatMessageAttachmentSave(
            id = file.file_id,
            chat_id = chat_id,
            message_id = message_id,
            size = file.file_size,
            last_url = file.file_path,
            last_url_until = last_url_until,
            extension = extension,
            mime_type = mime_type,
        )

    def nearest_hour_epoch(self) -> int:
        last_hour_mark: datetime = datetime.now().replace(minute = 0, second = 0, microsecond = 0)
        next_hour_mark: datetime = last_hour_mark + timedelta(hours = 1)
        self.sprint(f"Last hour mark: {next_hour_mark}")
        return int(next_hour_mark.timestamp())
