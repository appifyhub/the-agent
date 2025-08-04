from datetime import datetime, timedelta

import requests

from db.schema.chat_message_attachment import ChatMessageAttachment, ChatMessageAttachmentSave
from di.di import DI
from features.chat.supported_files import KNOWN_FILE_FORMATS
from features.chat.telegram.model.attachment.file import File
from util import log
from util.config import config
from util.functions import first_key_with_value


# Must be separated like this for now due to circular imports (thanks Python)
class TelegramBotSDKUtils:

    @staticmethod
    def refresh_attachments_by_ids(di: DI, attachment_ids: list[str]) -> list[ChatMessageAttachment]:
        log.d(f"Refreshing {len(attachment_ids)} attachments by IDs")
        attachments: list[ChatMessageAttachment] = []
        for attachment_id in attachment_ids:
            attachment_db = di.chat_message_attachment_crud.get(attachment_id)
            if not attachment_db:
                raise ValueError(f"Attachment with ID '{attachment_id}' not found in DB")
            attachments.append(ChatMessageAttachment.model_validate(attachment_db))
        return TelegramBotSDKUtils.refresh_attachment_instances(di, attachments)

    @staticmethod
    def refresh_attachment_instances(di: DI, attachments: list[ChatMessageAttachment]) -> list[ChatMessageAttachment]:
        log.d(f"Refreshing {len(attachments)} attachment instances")
        return [TelegramBotSDKUtils.refresh_attachment(di, attachment) for attachment in attachments]

    @staticmethod
    def refresh_attachment(
        di: DI,
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
            instance_db = di.chat_message_attachment_crud.get(
                str(attachment_save.id),
            ) or di.chat_message_attachment_crud.get_by_ext_id(str(attachment_save.ext_id))
            instance = ChatMessageAttachment.model_validate(instance_db) if instance_db else None
            instance_save = ChatMessageAttachmentSave(**instance.model_dump()) if instance else attachment_save
        else:
            raise ValueError("No attachment instance provided")

        # check if instance data is already fresh
        if not instance_save.has_stale_data:
            log.t(f"Attachment '{instance_save.id}': data is already fresh")
            # we store it anyway because it may contain fresh data from the API
            instance_db = di.chat_message_attachment_crud.save(instance_save)
            return ChatMessageAttachment.model_validate(instance_db)

        # data is stale or missing, we need to fetch the attachment data from remote
        if not instance_save.ext_id:
            raise ValueError(log.e("No external ID provided for the attachment"))
        log.t(f"Refreshing attachment data for external ID '{instance_save.ext_id}' (ext_id)")
        api_file: File = di.telegram_bot_api.get_file_info(instance_save.ext_id)

        # let's populate the attachment with the data from the API
        instance_save.size = api_file.file_size or instance_save.size
        if api_file.file_path:
            file_api_endpoint = f"{config.telegram_api_base_url}/file"
            bot_token = config.telegram_bot_token.get_secret_value()
            instance_save.last_url = f"{file_api_endpoint}/bot{bot_token}/{api_file.file_path}"
            instance_save.last_url_until = TelegramBotSDKUtils.__nearest_hour_epoch()

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
                TelegramBotSDKUtils.__detect_and_set_image_format(instance_save)

        # final version of the attachment is ready, store it
        result_db = di.chat_message_attachment_crud.save(instance_save)
        return ChatMessageAttachment.model_validate(result_db)

    @staticmethod
    def __detect_image_format_from_bytes(content: bytes) -> str | None:
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

    @staticmethod
    def __detect_and_set_image_format(instance_save: ChatMessageAttachmentSave) -> None:
        log.d("Both extension and mime_type are None, detecting from content")
        if not instance_save.last_url:
            return
        try:
            response = requests.get(instance_save.last_url, timeout = 10)
            if response.status_code == 200:
                detected_format = TelegramBotSDKUtils.__detect_image_format_from_bytes(response.content)
                if detected_format and detected_format in KNOWN_FILE_FORMATS:
                    # Detected format names match our KNOWN_FILE_FORMATS keys directly
                    instance_save.extension = detected_format
                    instance_save.mime_type = KNOWN_FILE_FORMATS[detected_format]
                    log.t(f"Detected format: {detected_format} -> {instance_save.mime_type}")
        except Exception as e:
            log.w("Failed to detect image format", e)

    @staticmethod
    def __nearest_hour_epoch() -> int:
        now = datetime.now()
        last_hour_mark: datetime = now.replace(minute = 0, second = 0, microsecond = 0)
        next_hour_mark: datetime = last_hour_mark + timedelta(hours = 1)
        log.t(f"Nearest hour at {now} is {next_hour_mark}")
        return int(next_hour_mark.timestamp())
