import base64
from datetime import timedelta, datetime
from enum import Enum
from uuid import UUID

import requests

from db.crud.chat_config import ChatConfigCRUD
from db.crud.chat_message import ChatMessageCRUD
from db.crud.chat_message_attachment import ChatMessageAttachmentCRUD
from db.crud.tools_cache import ToolsCacheCRUD
from db.crud.user import UserCRUD
from db.model.user import UserDB
from db.schema.chat_config import ChatConfig
from db.schema.chat_message_attachment import ChatMessageAttachment
from db.schema.tools_cache import ToolsCache, ToolsCacheSave
from db.schema.user import User
from features.audio.audio_transcriber import AudioTranscriber
from features.chat.supported_files import KNOWN_IMAGE_FORMATS, KNOWN_AUDIO_FORMATS, KNOWN_DOCS_FORMATS
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.chat.telegram.sdk.telegram_bot_sdk_utils import TelegramBotSDKUtils
from features.documents.document_search import DocumentSearch
from features.images.computer_vision_analyzer import ComputerVisionAnalyzer
from util.config import config
from util.functions import digest_md5
from util.safe_printer_mixin import SafePrinterMixin

CACHE_PREFIX = "attachments-content-resolver"
CACHE_TTL = timedelta(weeks = 13)


class AttachmentsContentResolver(SafePrinterMixin):
    class Result(Enum):
        failed = "Failed"
        partial = "Partial"
        success = "Success"

    # the following two lists are in sync
    attachments: list[ChatMessageAttachment | None]
    contents: list[str | None]

    __chat_config: ChatConfig
    __additional_context: str | None
    __invoker: User

    __bot_sdk: TelegramBotSDK
    __user_dao: UserCRUD
    __chat_config_dao: ChatConfigCRUD
    __chat_message_dao: ChatMessageCRUD
    __chat_message_attachment_dao: ChatMessageAttachmentCRUD
    __cache_dao: ToolsCacheCRUD

    def __init__(
        self,
        chat_id: str,
        invoker_user_id_hex: str,
        additional_context: str | None,
        attachment_ids: list[str],
        bot_sdk: TelegramBotSDK,
        user_dao: UserCRUD,
        chat_config_dao: ChatConfigCRUD,
        chat_message_dao: ChatMessageCRUD,
        chat_message_attachment_dao: ChatMessageAttachmentCRUD,
        cache_dao: ToolsCacheCRUD,
    ):
        super().__init__(config.verbose)
        self.attachments = []
        self.contents = []
        self.__additional_context = additional_context
        self.__bot_sdk = bot_sdk
        self.__user_dao = user_dao
        self.__chat_config_dao = chat_config_dao
        self.__chat_message_dao = chat_message_dao
        self.__chat_message_attachment_dao = chat_message_attachment_dao
        self.__cache_dao = cache_dao
        self.__validate(chat_id, invoker_user_id_hex)
        self.attachments = TelegramBotSDKUtils.refresh_attachments(
            sources = attachment_ids,
            chat_message_attachment_dao = chat_message_attachment_dao,
            bot_api = bot_sdk.api,
        )

    def __validate(self, chat_id: str, invoker_user_id_hex: str):
        self.sprint(f"Validating user '{invoker_user_id_hex}' and attachment resolution for chat '{chat_id}'")
        # check if chat exists
        chat_config_db = self.__chat_config_dao.get(chat_id)
        if not chat_config_db:
            message = f"Chat '{chat_id}' not found"
            self.sprint(message)
            raise ValueError(message)
        self.__chat_config = ChatConfig.model_validate(chat_config_db)
        # check if invoker exists
        invoker_user_db = self.__user_dao.get(UUID(hex = invoker_user_id_hex))
        if not invoker_user_db:
            message = f"Invoker '{invoker_user_id_hex}' not found"
            self.sprint(message)
            raise ValueError(message)
        self.__invoker = User.model_validate(invoker_user_db)
        # check if invoker has enough access rights
        if self.__invoker.group < UserDB.Group.beta:
            message = f"Invoker '{invoker_user_id_hex}' is not allowed to resolve attachments"
            self.sprint(message)
            raise ValueError(message)

    @property
    def resolution_status(self) -> Result:
        if not self.attachments:
            return AttachmentsContentResolver.Result.failed
        all_attachments_exist = all(attachment is not None for attachment in self.attachments)
        all_contents_exist = all(content is not None for content in self.contents)
        contents_match_attachments = len(self.attachments) == len(self.contents)
        # failure -> there are no attachments || some attachments are None || attachments don't match contents
        if not all_attachments_exist or not contents_match_attachments:
            return AttachmentsContentResolver.Result.failed
        # success -> all attachments and their contents are non-None && attachments match contents
        if all_attachments_exist and all_contents_exist and contents_match_attachments:
            return AttachmentsContentResolver.Result.success
        # partial -> some attachments are None || some attachments don't match contents || contents are None
        return AttachmentsContentResolver.Result.partial

    @property
    def resolution_result(self) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        for attachment, content in zip(self.attachments, self.contents):
            if attachment is not None:
                attachment_data = {
                    "id": attachment.id,
                    "text_content": content if content is not None else "<unresolved>",
                    "type": attachment.mime_type if attachment.mime_type else "<unknown>",
                }
                result.append(attachment_data)
        return result

    def execute(self) -> Result:
        self.sprint("Resolving attachments content")

        self.contents = []
        for attachment in self.attachments:
            # assuming the URL will never change... users might ask more questions about the same attachment
            additional_content_hash = digest_md5(self.__additional_context) if self.__additional_context else "*"
            unique_identifier = f"{attachment.id}-{additional_content_hash}"
            cache_key = self.__cache_dao.create_key(CACHE_PREFIX, unique_identifier)
            cache_entry_db = self.__cache_dao.get(cache_key)
            if cache_entry_db:
                cache_entry = ToolsCache.model_validate(cache_entry_db)
                if not cache_entry.is_expired():
                    self.sprint(f"Cache hit for '{cache_key}'")
                    self.contents.append(cache_entry.value)
                    continue
                self.sprint(f"Cache expired for '{cache_key}'")
            self.sprint(f"Cache miss for '{cache_key}'")
            try:
                content = self.fetch_text_content(attachment)
                if content is not None:
                    self.__cache_dao.save(
                        ToolsCacheSave(
                            key = cache_key,
                            value = content,
                            expires_at = datetime.now() + CACHE_TTL,
                        )
                    )
                self.contents.append(content)
            except Exception as e:
                self.sprint(f"Error resolving contents for '{attachment.id}'", e)
                self.contents.append(None)

        result = self.resolution_status
        self.sprint(f"Resolution result: {result}")
        return result

    def fetch_text_content(self, attachment: ChatMessageAttachment) -> str | None:
        self.sprint(f"Resolving text content for attachment '{attachment.id}'")

        # fetching binary contents will also validate the URL
        contents = requests.get(attachment.last_url).content

        # handle images
        if attachment.mime_type in KNOWN_IMAGE_FORMATS.values() or attachment.extension in KNOWN_IMAGE_FORMATS.keys():
            return ComputerVisionAnalyzer(
                job_id = attachment.id,
                image_mime_type = attachment.mime_type,
                open_ai_api_key = self.__invoker.open_ai_key,
                image_b64 = base64.b64encode(contents).decode("utf-8"),
                additional_context = self.__additional_context,
            ).execute()

        # handle audio
        if attachment.mime_type in KNOWN_AUDIO_FORMATS.values() or attachment.extension in KNOWN_AUDIO_FORMATS.keys():
            return AudioTranscriber(
                job_id = attachment.id,
                audio_url = attachment.last_url,
                open_ai_api_key = self.__invoker.open_ai_key,
                def_extension = attachment.extension,
                audio_content = contents,
                language_name = self.__chat_config.language_name,
                language_iso_code = self.__chat_config.language_iso_code,
            ).execute()

        # handle documents
        if attachment.mime_type in KNOWN_DOCS_FORMATS.values() or attachment.extension in KNOWN_DOCS_FORMATS.keys():
            return DocumentSearch(
                job_id = attachment.id,
                document_url = attachment.last_url,
                open_ai_api_key = self.__invoker.open_ai_key,
                additional_context = self.__additional_context,
            ).execute()

        self.sprint(f"Unsupported attachment '{attachment.id}': {attachment.mime_type}; '.{attachment.extension}'")
        return None
