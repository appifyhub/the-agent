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
from features.audio.audio_transcriber import KNOWN_AUDIO_FORMATS
from features.chat.telegram.telegram_bot_api import TelegramBotAPI
from features.chat.telegram.telegram_domain_mapper import TelegramDomainMapper
from features.documents.document_search import KNOWN_DOCS_FORMATS
from features.images.computer_vision_analyzer import KNOWN_IMAGE_FORMATS
from util.config import config
from util.functions import is_the_agent, nearest_hour_epoch, first_key_with_value
from util.safe_printer_mixin import SafePrinterMixin

KNOWN_FILE_FORMATS = KNOWN_IMAGE_FORMATS | KNOWN_AUDIO_FORMATS | KNOWN_DOCS_FORMATS


class TelegramDataResolver(SafePrinterMixin):
    """
    Resolves the final set of data attributes ready to be used by the service.
    If needed, this resolver will fetch more data from the API or the database.
    """

    class Result(BaseModel):
        chat: ChatConfig
        author: User | None
        message: ChatMessage
        attachments: List[ChatMessageAttachment]

    __session: Session
    __bot_api: TelegramBotAPI

    def __init__(self, session: Session, api: TelegramBotAPI):
        super().__init__(config.verbose)
        self.__session = session
        self.__bot_api = api

    def resolve(self, mapping_result: TelegramDomainMapper.Result) -> Result:
        # self.sprint(f"Resolving mapping result: {mapping_result}")
        resolved_chat_config = self.resolve_chat_config(mapping_result.chat)
        resolved_author: User | None = None
        if mapping_result.author:
            if is_the_agent(mapping_result.author):
                mapping_result.author.telegram_chat_id = None  # bot has no private chat
            resolved_author = self.resolve_author(mapping_result.author)
            mapping_result.message.author_id = resolved_author.id
        resolved_chat_message = self.resolve_chat_message(mapping_result.message)
        resolved_attachments = [
            self.resolve_chat_message_attachment(attachment) for attachment in mapping_result.attachments
        ]
        return TelegramDataResolver.Result(
            chat = resolved_chat_config,
            author = resolved_author,
            message = resolved_chat_message,
            attachments = resolved_attachments,
        )

    def resolve_chat_config(self, mapped_data: ChatConfigSave) -> ChatConfig:
        # self.sprint(f"Resolving chat config: {mapped_data}")
        db = ChatConfigCRUD(self.__session)
        old_chat_config_db = db.get(mapped_data.chat_id)
        if old_chat_config_db:
            old_chat_config = ChatConfig.model_validate(old_chat_config_db)
            # reset the attributes that are not normally changed through the Telegram API
            mapped_data.language_iso_code = old_chat_config.language_iso_code
            mapped_data.language_name = old_chat_config.language_name
            mapped_data.is_private = old_chat_config.is_private
            mapped_data.reply_chance_percent = old_chat_config.reply_chance_percent
        return ChatConfig.model_validate(db.save(mapped_data))

    def resolve_author(self, mapped_data: UserSave | None) -> User | None:
        if not mapped_data:
            return None
        # self.sprint(f"Resolving user: {mapped_data}")
        db = UserCRUD(self.__session)
        old_user_db = (
            db.get_by_telegram_user_id(mapped_data.telegram_user_id) or
            db.get_by_telegram_username(mapped_data.telegram_username)
        )

        if old_user_db:
            old_user = User.model_validate(old_user_db)
            # reset the attributes that are not normally changed through the Telegram API
            mapped_data.id = old_user.id
            mapped_data.telegram_chat_id = mapped_data.telegram_chat_id or old_user.telegram_chat_id
            mapped_data.open_ai_key = old_user.open_ai_key
            mapped_data.group = old_user.group
        else:
            # new users can only be added until the user limit is reached
            user_count = db.count()
            if user_count >= config.max_users:
                self.sprint(f"User limit reached: {user_count}/{config.max_users}")
                raise ValueError("User limit reached, try again later")
        return User.model_validate(db.save(mapped_data))

    def resolve_chat_message(self, mapped_data: ChatMessageSave) -> ChatMessage:
        # self.sprint(f"Resolving chat message: {mapped_data}")
        db = ChatMessageCRUD(self.__session)
        old_chat_message_db = db.get(mapped_data.chat_id, mapped_data.message_id)
        if old_chat_message_db:
            old_chat_message = ChatMessage.model_validate(old_chat_message_db)
            # reset the attributes that are not normally changed through the Telegram API
            mapped_data.author_id = mapped_data.author_id or old_chat_message.author_id
            mapped_data.sent_at = mapped_data.sent_at or old_chat_message.sent_at
        return ChatMessage.model_validate(db.save(mapped_data))

    def resolve_chat_message_attachment(self, mapped_data: ChatMessageAttachmentSave) -> ChatMessageAttachment:
        # self.sprint(f"Resolving chat message attachment: {mapped_data}")
        db = ChatMessageAttachmentCRUD(self.__session)
        old_attachment_db = db.get(mapped_data.id)
        if old_attachment_db:
            old_attachment = ChatMessageAttachment.model_validate(old_attachment_db)
            # reset the attributes that are not normally changed through the Telegram API
            mapped_data.size = mapped_data.size or old_attachment.size
            mapped_data.last_url = mapped_data.last_url or old_attachment.last_url
            mapped_data.last_url_until = mapped_data.last_url_until or old_attachment.last_url_until
            mapped_data.extension = mapped_data.extension or old_attachment.extension
            mapped_data.mime_type = mapped_data.mime_type or old_attachment.mime_type
        _ = self.update_attachment_using_api(mapped_data)  # _ was 'is_updated'
        # self.sprint(f"Is attachment updated via API? {is_updated}")
        return ChatMessageAttachment.model_validate(db.save(mapped_data))

    def update_attachment_using_api(self, attachment: ChatMessageAttachmentSave) -> bool:
        if not attachment.has_stale_data:
            return False
        # self.sprint(f"Updating attachment using API data. URL is now {attachment.last_url}")
        # self.sprint(
        #     f"\tExpires {"<unset>" if not attachment.last_url_until
        #     else f"at {datetime.fromtimestamp(attachment.last_url_until)}"}"
        # )

        api_file = self.__bot_api.get_file_info(attachment.id)
        extension: str | None = None
        last_url: str | None = None
        last_url_until: int | None = None
        mime_type: str | None = attachment.mime_type
        if api_file.file_path:
            last_url = f"{config.telegram_api_base_url}/file/bot{config.telegram_bot_token}/{api_file.file_path}"
            last_url_until = nearest_hour_epoch()
            if "." in api_file.file_path:
                # file path includes an extension
                extension = api_file.file_path.lower().split(".")[-1]
                if not attachment.mime_type:
                    mime_type = KNOWN_FILE_FORMATS.get(extension)
            else:
                # file path is without extension
                if attachment.mime_type:
                    extension = first_key_with_value(KNOWN_FILE_FORMATS, attachment.mime_type)

        # self.sprint(f"Resolved:\n\textension '.{extension}'\n\tmime-type '{mime_type}'")
        attachment.size = api_file.file_size
        attachment.last_url = last_url
        attachment.last_url_until = last_url_until
        attachment.extension = extension
        attachment.mime_type = mime_type
        return True
