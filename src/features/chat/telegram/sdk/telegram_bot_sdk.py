import time
from datetime import datetime, timedelta
from typing import Literal

import requests

from db.schema.chat_message import ChatMessage
from db.schema.chat_message_attachment import ChatMessageAttachment, ChatMessageAttachmentSave
from di.di import DI
from features.chat.supported_files import KNOWN_FILE_FORMATS
from features.chat.telegram.model.attachment.file import File
from features.chat.telegram.model.chat_member import ChatMember
from features.chat.telegram.model.message import Message
from features.chat.telegram.model.update import Update
from util import log
from util.config import config
from util.error_codes import ATTACHMENT_NOT_FOUND, MISSING_EXTERNAL_ATTACHMENT_ID, NO_ATTACHMENT_INSTANCE, PLATFORM_MAPPING_FAILED
from util.errors import InternalError, NotFoundError
from util.functions import first_key_with_value


class TelegramBotSDK:

    __di: DI

    def __init__(self, di: DI):
        self.__di = di

    # === API functions ===

    def send_text_message(
        self,
        chat_id: int | str,
        text: str,
        parse_mode: str = "markdown",
        disable_notification: bool = False,
        link_preview_options: dict | None = None,
    ) -> ChatMessage:
        sent_message = self.__di.telegram_bot_api.send_text_message(
            chat_id = chat_id,
            text = text,
            parse_mode = parse_mode,
            disable_notification = disable_notification,
            link_preview_options = link_preview_options,
        )
        return self.__store_api_response_as_message(sent_message)

    def send_photo(
        self,
        chat_id: int | str,
        photo_url: str,
        caption: str | None = None,
        parse_mode: str = "markdown",
        disable_notification: bool = False,
    ) -> ChatMessage:
        sent_message = self.__di.telegram_bot_api.send_photo(
            chat_id = chat_id,
            photo_url = photo_url,
            caption = caption,
            parse_mode = parse_mode,
            disable_notification = disable_notification,
        )
        return self.__store_api_response_as_message(sent_message)

    def send_document(
        self,
        chat_id: int | str,
        document_url: str,
        parse_mode: str = "markdown",
        thumbnail: str | None = None,
        caption: str | None = None,
        disable_notification: bool = False,
    ) -> ChatMessage:
        sent_message = self.__di.telegram_bot_api.send_document(
            chat_id = chat_id,
            document_url = document_url,
            caption = caption,
            parse_mode = parse_mode,
            thumbnail = thumbnail,
            disable_notification = disable_notification,
        )
        return self.__store_api_response_as_message(sent_message)

    def set_status_typing(self, chat_id: int | str):
        self.__di.telegram_bot_api.set_status_typing(chat_id)

    def set_status_uploading_image(self, chat_id: int | str):
        self.__di.telegram_bot_api.set_status_uploading_image(chat_id)

    def set_chat_action(self, chat_id: int | str, action: Literal["typing", "upload_photo"]):
        if action == "upload_photo":
            self.set_status_uploading_image(chat_id)
        else:
            self.set_status_typing(chat_id)

    def set_reaction(self, chat_id: int | str, message_id: int | str, reaction: str | None):
        self.__di.telegram_bot_api.set_reaction(chat_id = chat_id, message_id = message_id, reaction = reaction)

    def send_button_link(self, chat_id: int | str, link_url: str, button_text: str = "⚙️") -> ChatMessage:
        sent_message = self.__di.telegram_bot_api.send_button_link(chat_id, link_url, button_text)
        return self.__store_api_response_as_message(sent_message)

    def get_chat_member(self, chat_id: int | str, user_id: int | str) -> ChatMember | None:
        try:
            return self.__di.telegram_bot_api.get_chat_member(chat_id, user_id)
        except Exception as e:
            log.e(f"Failed to get chat member '{user_id}' from chat '{chat_id}'", e)
            return None

    def get_chat_administrators(self, chat_id: int | str) -> list[ChatMember] | None:
        try:
            return self.__di.telegram_bot_api.get_chat_administrators(chat_id)
        except Exception as e:
            log.e(f"Failed to get chat administrators for chat '{chat_id}'", e)
            return None

    # === Data utilities ===

    def __store_api_response_as_message(self, raw_api_response: dict) -> ChatMessage:
        log.t("Storing API message data...")
        message = Message(**raw_api_response["result"])
        update = Update(update_id = time.time_ns(), message = message)
        mapping_result = self.__di.telegram_domain_mapper.map_update(update)
        if not mapping_result:
            raise InternalError(f"Telegram API domain mapping failed for local update '{update.update_id}'", PLATFORM_MAPPING_FAILED)  # noqa: E501
        resolution_result = self.__di.telegram_data_resolver.resolve(mapping_result)
        if not resolution_result.message:
            raise InternalError(f"Telegram data resolution failed for local update '{update.update_id}'", PLATFORM_MAPPING_FAILED)
        # noinspection PyTypeChecker
        return resolution_result.message

    def refresh_attachments_by_ids(self, attachment_ids: list[str]) -> list[ChatMessageAttachment]:
        log.d(f"Refreshing {len(attachment_ids)} attachments by IDs")
        attachments: list[ChatMessageAttachment] = []
        for attachment_id in attachment_ids:
            attachment_db = self.__di.chat_message_attachment_crud.get(attachment_id)
            if not attachment_db:
                raise NotFoundError(f"Attachment with ID '{attachment_id}' not found in DB", ATTACHMENT_NOT_FOUND)
            attachments.append(ChatMessageAttachment.model_validate(attachment_db))
        return self.refresh_attachment_instances(attachments)

    def refresh_attachment_instances(self, attachments: list[ChatMessageAttachment]) -> list[ChatMessageAttachment]:
        log.d(f"Refreshing {len(attachments)} attachment instances")
        return [self.refresh_attachment(attachment) for attachment in attachments]

    def refresh_attachment(
        self,
        attachment: ChatMessageAttachment | None = None,
        attachment_save: ChatMessageAttachmentSave | None = None,
    ) -> ChatMessageAttachment:
        # try to resolve the local save instance of the attachment
        instance_save: ChatMessageAttachmentSave
        if attachment:
            log.d(f"Refreshing attachment '{attachment.id}' (instance)")
            instance_save = attachment_save or ChatMessageAttachmentSave(**attachment.model_dump())
        elif attachment_save:
            log.d(f"Refreshing attachment '{attachment_save.id}' (save instance)")
            instance_db = self.__di.chat_message_attachment_crud.get(
                str(attachment_save.id),
            ) or self.__di.chat_message_attachment_crud.get_by_external_id(str(attachment_save.external_id))
            instance = ChatMessageAttachment.model_validate(instance_db) if instance_db else None
            instance_save = ChatMessageAttachmentSave(**instance.model_dump()) if instance else attachment_save
        else:
            raise InternalError("No attachment instance provided", NO_ATTACHMENT_INSTANCE)

        # check if instance data is already fresh
        if not instance_save.has_stale_data:
            log.t(f"Attachment '{instance_save.id}': data is already fresh")
            # we store it anyway because it may contain fresh data from the API
            instance_db = self.__di.chat_message_attachment_crud.save(instance_save)
            return ChatMessageAttachment.model_validate(instance_db)

        # data is stale or missing, we need to fetch the attachment data from remote
        if not instance_save.external_id:
            raise InternalError("No external ID provided for the attachment", MISSING_EXTERNAL_ATTACHMENT_ID)
        log.t(f"Refreshing attachment data for external ID '{instance_save.external_id}'")
        api_file: File = self.__di.telegram_bot_api.get_file_info(instance_save.external_id)

        # let's populate the attachment with the data from the API
        instance_save.size = api_file.file_size or instance_save.size
        if api_file.file_path:
            file_api_endpoint = f"{config.telegram_api_base_url}/file"
            bot_token = config.telegram_bot_token.get_secret_value()
            instance_save.last_url = f"{file_api_endpoint}/bot{bot_token}/{api_file.file_path}"
            instance_save.last_url_until = self._nearest_hour_epoch()

        # let's set the additional available properties
        if not instance_save.extension:
            if api_file.file_path and "." in api_file.file_path:
                instance_save.extension = api_file.file_path.lower().split(".")[-1] or instance_save.extension
                if not instance_save.mime_type and instance_save.extension:
                    instance_save.mime_type = KNOWN_FILE_FORMATS.get(instance_save.extension) or instance_save.mime_type
            elif instance_save.mime_type:
                # reverse engineer the extension
                instance_save.extension = (
                    first_key_with_value(KNOWN_FILE_FORMATS, instance_save.mime_type) or instance_save.extension
                )
            elif instance_save.last_url:
                self._detect_and_set_image_format(instance_save)

        # final version of the attachment is ready, store it
        result_db = self.__di.chat_message_attachment_crud.save(instance_save)
        return ChatMessageAttachment.model_validate(result_db)

    @staticmethod
    def _detect_image_format_from_bytes(content: bytes) -> str | None:
        """Detect image format from magic bytes"""
        if len(content) < 8:
            return None
        # PNG: 89 50 4E 47 0D 0A 1A 0A
        if content[:8] == b"\x89PNG\r\n\x1a\n":
            return "png"
        # JPEG: FF D8 FF
        if content[:3] == b"\xff\xd8\xff":
            return "jpeg"
        # GIF: GIF87a or GIF89a
        if content[:6] in (b"GIF87a", b"GIF89a"):
            return "gif"
        # BMP: BM
        if content[:2] == b"BM":
            return "bmp"
        # WEBP: RIFF....WEBP
        if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
            return "webp"
        # TIFF: II*\x00 (little-endian) or MM\x00* (big-endian)
        if content[:4] in (b"II*\x00", b"MM\x00*"):
            return "tiff"
        return None

    def _detect_and_set_image_format(self, instance_save: ChatMessageAttachmentSave) -> None:
        log.d("Both extension and mime_type are None, detecting from content")
        if not instance_save.last_url:
            return
        try:
            response = requests.get(instance_save.last_url, timeout = 10)
            if response.status_code == 200:
                detected_format = self._detect_image_format_from_bytes(response.content)
                if detected_format and detected_format in KNOWN_FILE_FORMATS:
                    # detected format names match our KNOWN_FILE_FORMATS keys directly
                    instance_save.extension = detected_format
                    instance_save.mime_type = KNOWN_FILE_FORMATS[detected_format]
                    log.t(f"Detected format: {detected_format} -> {instance_save.mime_type}")
        except Exception as e:
            log.w("Failed to detect image format", e)

    @staticmethod
    def _nearest_hour_epoch() -> int:
        now = datetime.now()
        last_hour_mark: datetime = now.replace(minute = 0, second = 0, microsecond = 0)
        next_hour_mark: datetime = last_hour_mark + timedelta(hours = 1)
        log.t(f"Nearest hour at {now} is {next_hour_mark}")
        return int(next_hour_mark.timestamp())
