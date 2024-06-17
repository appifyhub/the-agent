from datetime import datetime, timedelta
from typing import List

from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.crud.chat_config import ChatConfigCRUD
from db.crud.chat_message import ChatMessageCRUD
from db.crud.chat_message_attachment import ChatMessageAttachmentCRUD
from db.crud.user import UserCRUD
from db.schema.chat_config import ChatConfigSave, ChatConfig
from db.schema.chat_message import ChatMessageSave, ChatMessage
from db.schema.chat_message_attachment import ChatMessageAttachmentSave, ChatMessageAttachment
from db.schema.user import UserSave, User
from features.chat.telegram.bot_api import BotAPI
from features.chat.telegram.converter import ConversionResult
from util.config import config
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


class ResolutionResult(BaseModel):
    chat: ChatConfig
    author: User | None
    message: ChatMessage
    attachments: List[ChatMessageAttachment]


class Resolver(SafePrinterMixin):
    """
    Resolves the final set of data attributes ready to be used by the service.
    If needed, this resolver will fetch more data from the API or the database.
    """

    __session: Session
    __bot_api: BotAPI

    def __init__(self, session: Session, api: BotAPI):
        super().__init__(config.verbose)
        self.__session = session
        self.__bot_api = api

    def resolve(self, conversion_result: ConversionResult) -> ResolutionResult:
        self.sprint(f"Resolving conversion result: {conversion_result}")
        resolved_chat_config = self.resolve_chat_config(conversion_result.chat)
        resolved_author: User | None = None
        if conversion_result.author:
            if config.telegram_bot_username == conversion_result.author.telegram_username:
                conversion_result.author.telegram_chat_id = None  # bot has no private chat
            resolved_author = self.resolve_author(conversion_result.author)
            conversion_result.message.author_id = resolved_author.id
        resolved_chat_message = self.resolve_chat_message(conversion_result.message)
        resolved_attachments = [
            self.resolve_chat_message_attachment(attachment) for attachment in conversion_result.attachments
        ]
        return ResolutionResult(
            chat = resolved_chat_config,
            author = resolved_author,
            message = resolved_chat_message,
            attachments = resolved_attachments,
        )

    def resolve_chat_config(self, converted_data: ChatConfigSave) -> ChatConfig:
        self.sprint(f"Resolving chat config: {converted_data}")
        db = ChatConfigCRUD(self.__session)
        old_chat_config_db = db.get(converted_data.chat_id)
        if old_chat_config_db:
            old_chat_config = ChatConfig.model_validate(old_chat_config_db)
            # reset the attributes that are not normally changed through the Telegram API
            converted_data.persona_code = old_chat_config.persona_code
            converted_data.persona_name = old_chat_config.persona_name
            converted_data.language_iso_code = old_chat_config.language_iso_code
            converted_data.language_name = old_chat_config.language_name
            converted_data.is_private = old_chat_config.is_private
        return ChatConfig.model_validate(db.save(converted_data))

    def resolve_author(self, converted_data: UserSave | None) -> User | None:
        if not converted_data: return None
        self.sprint(f"Resolving user: {converted_data}")
        db = UserCRUD(self.__session)
        old_user_db = db.get_by_telegram_user_id(converted_data.telegram_user_id)
        if old_user_db:
            old_user = User.model_validate(old_user_db)
            # reset the attributes that are not normally changed through the Telegram API
            converted_data.id = old_user.id
            converted_data.open_ai_key = old_user.open_ai_key
            converted_data.group = old_user.group
        return User.model_validate(db.save(converted_data))

    def resolve_chat_message(self, converted_data: ChatMessageSave) -> ChatMessage:
        self.sprint(f"Resolving chat message: {converted_data}")
        db = ChatMessageCRUD(self.__session)
        old_chat_message_db = db.get(converted_data.chat_id, converted_data.message_id)
        if old_chat_message_db:
            old_chat_message = ChatMessage.model_validate(old_chat_message_db)
            # reset the attributes that are not normally changed through the Telegram API
            converted_data.author_id = converted_data.author_id or old_chat_message.author_id
            converted_data.sent_at = converted_data.sent_at or old_chat_message.sent_at
        return ChatMessage.model_validate(db.save(converted_data))

    def resolve_chat_message_attachment(self, converted_data: ChatMessageAttachmentSave) -> ChatMessageAttachment:
        self.sprint(f"Resolving chat message attachment: {converted_data}")
        db = ChatMessageAttachmentCRUD(self.__session)
        old_attachment_db = db.get(converted_data.id)
        if old_attachment_db:
            old_attachment = ChatMessageAttachment.model_validate(old_attachment_db)
            # reset the attributes that are not normally changed through the Telegram API
            converted_data.size = converted_data.size or old_attachment.size
            converted_data.last_url = converted_data.last_url or old_attachment.last_url
            converted_data.last_url_until = converted_data.last_url_until or old_attachment.last_url_until
            converted_data.extension = converted_data.extension or old_attachment.extension
            converted_data.mime_type = converted_data.mime_type or old_attachment.mime_type
        is_updated = self.update_attachment_using_api(converted_data)
        self.sprint(f"Attachment updated via API: {is_updated}")
        return ChatMessageAttachment.model_validate(db.save(converted_data))

    def update_attachment_using_api(self, attachment: ChatMessageAttachmentSave) -> bool:
        is_missing_url = not attachment.last_url
        expiration_timestamp = attachment.last_url_until or 0
        is_url_expired = expiration_timestamp <= int(datetime.now().timestamp())

        if not is_missing_url and not is_url_expired: return False
        self.sprint(f"Updating attachment using API data. URL is {attachment.last_url}")
        self.sprint(f"\tExpiration at {datetime.fromtimestamp(expiration_timestamp)}")

        api_file = self.__bot_api.get_file_info(attachment.id)
        extension: str | None = None
        last_url: str | None = None
        last_url_until: int | None = None
        mime_type: str | None = attachment.mime_type
        if api_file.file_path and ("." in api_file.file_path):
            extension = api_file.file_path.lower().split(".")[-1]
            last_url = f"{config.telegram_api_base_url}/file/bot{config.telegram_bot_token}/{api_file.file_path}"
            last_url_until = self.nearest_hour_epoch()
            if not attachment.mime_type:
                mime_type = SUPPORTED_MIME_TYPES.get(extension, None)
        self.sprint(f"Resolved:\n\textension '.{extension}'\n\tmime-type '{mime_type}'")
        attachment.size = api_file.file_size
        attachment.last_url = last_url
        attachment.last_url_until = last_url_until
        attachment.extension = extension
        attachment.mime_type = mime_type
        return True

    def nearest_hour_epoch(self) -> int:
        now = datetime.now()
        last_hour_mark: datetime = now.replace(minute = 0, second = 0, microsecond = 0)
        next_hour_mark: datetime = last_hour_mark + timedelta(hours = 1)
        self.sprint(f"Nearest hour at {now} is {next_hour_mark}")
        return int(next_hour_mark.timestamp())
