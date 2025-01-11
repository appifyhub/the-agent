from datetime import datetime, timedelta

from db.crud.chat_message_attachment import ChatMessageAttachmentCRUD
from db.schema.chat_message_attachment import ChatMessageAttachmentSave, ChatMessageAttachment
from features.chat.supported_files import KNOWN_FILE_FORMATS
from features.chat.telegram.sdk.telegram_bot_api import TelegramBotAPI
from util.config import config
from util.functions import first_key_with_value
from util.safe_printer_mixin import sprint


# Must be separated like this for now due to circular imports (thanks Python)
class TelegramBotSDKUtils:

    @staticmethod
    def refresh_attachments(
        sources: list[ChatMessageAttachmentSave] | list[str],
        bot_api: TelegramBotAPI,
        chat_message_attachment_dao: ChatMessageAttachmentCRUD,
    ) -> list[ChatMessageAttachment]:
        sprint(f"Refreshing {len(sources)} attachments")
        if not sources:
            return []
        return [
            TelegramBotSDKUtils.refresh_attachment(attachment, bot_api, chat_message_attachment_dao)
            for attachment in sources
        ]

    @staticmethod
    def refresh_attachment(
        source: ChatMessageAttachmentSave | str,
        bot_api: TelegramBotAPI,
        chat_message_attachment_dao: ChatMessageAttachmentCRUD,
    ) -> ChatMessageAttachment:
        source_id = source if isinstance(source, str) else source.id
        sprint(f"Refreshing attachment data for '{source_id}'")

        # we either clone anyway to preserve the source data,
        # or create a fake instance to be able to manipulate the data
        clone: ChatMessageAttachmentSave
        should_fetch_from_db: bool
        if isinstance(source, ChatMessageAttachmentSave):
            should_fetch_from_db = source.has_stale_data
            clone = ChatMessageAttachmentSave(**source.model_dump())
        else:
            should_fetch_from_db = True
            clone = ChatMessageAttachmentSave(id = source_id, chat_id = "", message_id = "")
        # try to get from DB if missing core data or data is stale
        if should_fetch_from_db:
            fresh_data_db = chat_message_attachment_dao.get(source_id)
            if not fresh_data_db:
                message = f"Attachment {source_id} not found in DB"
                sprint(message)
                raise ValueError(message)
            fresh_data = ChatMessageAttachment.model_validate(fresh_data_db)
            clone = ChatMessageAttachmentSave(**fresh_data.model_dump())
        # if data is not stale, just store it and exit (can also be first store)
        if not clone.has_stale_data:
            sprint("\tAttachment data is fresh")
            result_db = chat_message_attachment_dao.save(clone)
            return ChatMessageAttachment.model_validate(result_db)

        # we need to fetch a fresh data object from API
        sprint("\tAttachment data is stale or not loaded yet")
        api_file = bot_api.get_file_info(source_id)
        clone.size = api_file.file_size or clone.size
        if api_file.file_path:
            file_api_endpoint = f"{config.telegram_api_base_url}/file"
            clone.last_url = f"{file_api_endpoint}/bot{config.telegram_bot_token}/{api_file.file_path}"
            clone.last_url_until = TelegramBotSDKUtils.__nearest_hour_epoch()
        # set additional properties (if not already resolved)
        if not clone.extension:
            if "." in api_file.file_path:
                clone.extension = api_file.file_path.lower().split(".")[-1] or clone.extension
                if not clone.mime_type:
                    clone.mime_type = KNOWN_FILE_FORMATS.get(clone.extension) or clone.mime_type
            elif clone.mime_type:
                # reverse engineer the extension
                clone.extension = first_key_with_value(KNOWN_FILE_FORMATS, clone.mime_type) or clone.extension

        result_db = chat_message_attachment_dao.save(clone)
        return ChatMessageAttachment.model_validate(result_db)

    @staticmethod
    def __nearest_hour_epoch() -> int:
        now = datetime.now()
        last_hour_mark: datetime = now.replace(minute = 0, second = 0, microsecond = 0)
        next_hour_mark: datetime = last_hour_mark + timedelta(hours = 1)
        sprint(f"Nearest hour at {now} is {next_hour_mark}")
        return int(next_hour_mark.timestamp())
