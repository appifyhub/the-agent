from datetime import datetime
from typing import List

from pydantic import BaseModel

from db.schema.chat_config import ChatConfigSave
from db.schema.chat_message import ChatMessageSave
from db.schema.chat_message_attachment import ChatMessageAttachmentSave
from db.schema.user import UserSave
from features.chat.telegram.model.attachment.file import File
from features.chat.telegram.model.message import Message
from features.chat.telegram.model.update import Update
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


class TelegramDomainMapper(SafePrinterMixin):
    """
    Maps the Telegram network models to domain models.
    """

    class Result(BaseModel):
        chat: ChatConfigSave
        author: UserSave | None
        message: ChatMessageSave
        attachments: List[ChatMessageAttachmentSave]

    def __init__(self):
        super().__init__(config.verbose)

    def map_update(self, update: Update) -> Result | None:
        # self.sprint(f"Mapping update: {update}")
        message = update.edited_message or update.message
        if not message:
            self.sprint(f"Nothing to map in update: {update}")
            return None
        result_chat = self.map_chat(message)
        result_author = self.map_author(message)
        result_message = self.map_message(message)
        result_attachments = self.map_attachments(message)
        return TelegramDomainMapper.Result(
            chat = result_chat,
            author = result_author,
            message = result_message,
            attachments = result_attachments,
        )

    def map_message(self, message: Message) -> ChatMessageSave:
        # self.sprint(f"Mapping message: {message}")
        return ChatMessageSave(
            chat_id = str(message.chat.id),
            message_id = str(message.message_id),
            sent_at = datetime.fromtimestamp(message.edit_date or message.date),
            text = self.map_text(message),
        )

    # noinspection PyMethodMayBeStatic
    def map_author(self, message: Message) -> UserSave | None:
        if not message.from_user:
            return None
        # self.sprint(f"Mapping author {message.from_user}")
        # properties might be updated later when this is stored
        author = message.from_user
        return UserSave(
            full_name = f"{author.first_name} {author.last_name}" if author.last_name else author.first_name,
            telegram_username = author.username,
            telegram_chat_id = str(message.chat.id) if message.chat.type == "private" else None,
            telegram_user_id = author.id,
        )

    def map_text_as_reply(self, message: Message) -> str:
        parts = []
        if message.caption:
            parts.append(f">>>> {message.caption}")
        if message.text:
            parts.append(f">>>> {message.text}")
        attachments_as_text = self.map_attachments_as_text(message)
        if attachments_as_text:
            parts.append(f">>>> 📎 {attachments_as_text}")
        # self.sprint(f"Mapping reply message text: {parts}")
        return "\n\n".join(parts)

    def map_text(self, message: Message) -> str:
        parts = []
        reply_text = self.map_text_as_reply(message.reply_to_message) if message.reply_to_message else None
        if reply_text:
            parts.append(f"{reply_text}")
        quote = message.quote.text if message.quote else None
        if quote:
            parts.append(f">> {quote}")
        if message.caption:
            parts.append(f"{message.caption}")
        if message.text:
            parts.append(message.text)
        attachments_as_text = self.map_attachments_as_text(message)
        if attachments_as_text:
            parts.append(f"📎 {attachments_as_text}")
        # self.sprint(f"Mapping message text: {parts}")
        return "\n\n".join(parts)

    def map_chat(self, message: Message) -> ChatConfigSave:
        chat = message.chat
        # self.sprint(f"Mapping chat: {chat}")
        title = self.resolve_chat_name(str(chat.id), chat.title, chat.username, chat.first_name, chat.last_name)
        language_code = message.from_user.language_code if message.from_user else None
        return ChatConfigSave(
            chat_id = str(chat.id),
            title = title,
            is_private = chat.type == "private",
            language_iso_code = language_code,
        )

    # noinspection PyMethodMayBeStatic
    def resolve_chat_name(
        self,
        chat_id: str,
        title: str | None,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
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
        # self.sprint(f"Resolved chat name {result}")
        return result

    def map_attachments_as_text(self, message: Message) -> str | None:
        attachments = self.map_attachments(message)
        if not attachments:
            return None
        formatted_attachments = [
            f"{attachment.id} ({attachment.mime_type})" if attachment.mime_type else f"{attachment.id}"
            for attachment in attachments
        ]
        # self.sprint(f"Mapping attachments: {formatted_attachments}")
        return f"[ {', '.join(formatted_attachments)} ]"

    def map_attachments(self, message: Message) -> List[ChatMessageAttachmentSave]:
        attachments: List[ChatMessageAttachmentSave] = []
        if message.audio:
            # self.sprint(f"Mapping audio: {message.audio}")
            dummy_file = File(
                file_id = message.audio.file_id,
                file_unique_id = message.audio.file_unique_id,
                file_size = message.audio.file_size,
            )
            attachments.append(
                self.map_to_attachment(
                    file = dummy_file,
                    chat_id = str(message.chat.id),
                    message_id = str(message.message_id),
                    mime_type = message.audio.mime_type,
                )
            )
        if message.document:
            # self.sprint(f"Mapping document: {message.document}")
            dummy_file = File(
                file_id = message.document.file_id,
                file_unique_id = message.document.file_unique_id,
                file_size = message.document.file_size,
            )
            attachments.append(
                self.map_to_attachment(
                    file = dummy_file,
                    chat_id = str(message.chat.id),
                    message_id = str(message.message_id),
                    mime_type = message.document.mime_type,
                )
            )
        if message.photo:
            largest_photo = max(message.photo, key = lambda size: size.width * size.height)
            # self.sprint(f"Mapping photo: {largest_photo}")
            dummy_file = File(
                file_id = largest_photo.file_id,
                file_unique_id = largest_photo.file_unique_id,
                file_size = largest_photo.file_size,
            )
            attachments.append(
                self.map_to_attachment(
                    file = dummy_file,
                    chat_id = str(message.chat.id),
                    message_id = str(message.message_id),
                    mime_type = None,
                )
            )
        if message.voice:
            # self.sprint(f"Mapping voice: {message.voice}")
            dummy_file = File(
                file_id = message.voice.file_id,
                file_unique_id = message.voice.file_unique_id,
                file_size = message.voice.file_size,
            )
            attachments.append(
                self.map_to_attachment(
                    file = dummy_file,
                    chat_id = str(message.chat.id),
                    message_id = str(message.message_id),
                    mime_type = message.voice.mime_type,
                )
            )
        return attachments

    # noinspection PyMethodMayBeStatic
    def map_to_attachment(
        self,
        file: File,
        chat_id: str,
        message_id: str,
        mime_type: str | None,
    ) -> ChatMessageAttachmentSave:
        # self.sprint(f"Creating attachment from file: {file}")
        last_url = f"{config.telegram_api_base_url}/file/bot{config.telegram_bot_token}/{file.file_path}"
        return ChatMessageAttachmentSave(
            id = file.file_id,
            chat_id = chat_id,
            message_id = message_id,
            size = file.file_size,
            last_url = last_url if file.file_path else None,
            mime_type = mime_type,
        )
