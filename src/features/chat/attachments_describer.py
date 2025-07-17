import base64
from datetime import datetime, timedelta
from enum import Enum

import requests

from db.schema.chat_message_attachment import ChatMessageAttachment
from db.schema.tools_cache import ToolsCache, ToolsCacheSave
from di.di import DI
from features.audio.audio_transcriber import AudioTranscriber
from features.chat.supported_files import KNOWN_AUDIO_FORMATS, KNOWN_DOCS_FORMATS, KNOWN_IMAGE_FORMATS
from features.chat.telegram.sdk.telegram_bot_sdk_utils import TelegramBotSDKUtils
from features.documents.document_search import DocumentSearch
from features.images.computer_vision_analyzer import ComputerVisionAnalyzer
from util.config import config
from util.functions import digest_md5
from util.safe_printer_mixin import SafePrinterMixin

CACHE_PREFIX = "attachments-describer"
CACHE_TTL = timedelta(weeks = 13)


class AttachmentsDescriber(SafePrinterMixin):
    class Result(Enum):
        failed = "Failed"
        partial = "Partial"
        success = "Success"

    # the following two lists are in sync
    __attachments: list[ChatMessageAttachment | None]
    __contents: list[str | None]

    __additional_context: str | None
    __di: DI

    def __init__(
        self,
        additional_context: str | None,
        attachment_ids: list[str],
        di: DI,
    ):
        super().__init__(config.verbose)
        self.__attachments = []
        self.__contents = []
        self.__additional_context = additional_context
        self.__di = di
        self.__validate(attachment_ids)

    def __validate(self, attachment_ids: list[str]) -> None:
        self.sprint(f"Validating {len(attachment_ids)} attachments in chat '{self.__di.invoker_chat_id}'")
        if not attachment_ids:
            message = "Malformed LLM Input Error: No attachment IDs provided. You may retry only once!"
            self.sprint(message)
            raise ValueError(message)
        for attachment_id in attachment_ids:
            if not attachment_id:
                message = "Malformed LLM Input Error: Attachment ID cannot be empty. You may retry only once!"
                self.sprint(message)
                raise ValueError(message)
            attachment_db = self.__di.chat_message_attachment_crud.get(attachment_id)
            if not attachment_db:
                message = f"Malformed LLM Input Error: Attachment '{attachment_id}' not found in DB. You may retry only once!"
                self.sprint(message)
                raise ValueError(message)
        self.__attachments = TelegramBotSDKUtils.refresh_attachments(
            sources = attachment_ids,
            chat_message_attachment_dao = self.__di.chat_message_attachment_crud,
            bot_api = self.__di.telegram_bot_api,
        )

    @property
    def resolution_status(self) -> Result:
        if not self.__attachments:
            return AttachmentsDescriber.Result.failed
        all_attachments_exist = all(attachment is not None for attachment in self.__attachments)
        all_contents_exist = all(content is not None for content in self.__contents)
        contents_match_attachments = len(self.__attachments) == len(self.__contents)
        # failure -> there are no attachments || some attachments are None || attachments don't match contents
        if not all_attachments_exist or not contents_match_attachments:
            return AttachmentsDescriber.Result.failed
        # success -> all attachments and their contents are non-None && attachments match contents
        if all_attachments_exist and all_contents_exist and contents_match_attachments:
            return AttachmentsDescriber.Result.success
        # partial -> some attachments are None || some attachments don't match contents || contents are None
        return AttachmentsDescriber.Result.partial

    @property
    def result(self) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        for attachment, content in zip(self.__attachments, self.__contents):
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

        self.__contents = []
        for attachment in self.__attachments:
            if attachment is None:
                self.sprint("Skipping None attachment")
                self.__contents.append(None)
                continue
            # assuming the URL will never change... users might ask more questions about the same attachment
            additional_content_hash = digest_md5(self.__additional_context) if self.__additional_context else "*"
            unique_identifier = f"{attachment.id}-{additional_content_hash}"
            cache_key = self.__di.tools_cache_crud.create_key(CACHE_PREFIX, unique_identifier)
            cache_entry_db = self.__di.tools_cache_crud.get(cache_key)
            if cache_entry_db:
                cache_entry = ToolsCache.model_validate(cache_entry_db)
                if not cache_entry.is_expired():
                    self.sprint(f"Cache hit for '{cache_key}'")
                    self.__contents.append(cache_entry.value)
                    continue
                self.sprint(f"Cache expired for '{cache_key}'")
            self.sprint(f"Cache miss for '{cache_key}'")
            try:
                content = self.fetch_text_content(attachment)
                if content is not None:
                    self.__di.tools_cache_crud.save(
                        ToolsCacheSave(
                            key = cache_key,
                            value = content,
                            expires_at = datetime.now() + CACHE_TTL,
                        ),
                    )
                self.__contents.append(content)
            except Exception as e:
                self.sprint(f"Error resolving contents for '{attachment.id}'", e)
                self.__contents.append(None)

        result = self.resolution_status
        self.sprint(f"Resolution result: {result}")
        return result

    def fetch_text_content(self, attachment: ChatMessageAttachment) -> str | None:
        self.sprint(f"Resolving text content for attachment '{attachment.id}'")

        # fetching binary contents will also validate the URL
        contents = requests.get(attachment.last_url).content

        # handle images
        if attachment.mime_type in KNOWN_IMAGE_FORMATS.values() or attachment.extension in KNOWN_IMAGE_FORMATS.keys():
            configured_tool = self.__di.tool_choice_resolver.require_tool(
                ComputerVisionAnalyzer.TOOL_TYPE,
                ComputerVisionAnalyzer.DEFAULT_TOOL,
            )
            return self.__di.computer_vision_analyzer(
                job_id = attachment.id,
                image_mime_type = attachment.mime_type,
                configured_tool = configured_tool,
                image_b64 = base64.b64encode(contents).decode("utf-8"),
                additional_context = self.__additional_context,
            ).execute()

        # handle audio
        if attachment.mime_type in KNOWN_AUDIO_FORMATS.values() or attachment.extension in KNOWN_AUDIO_FORMATS.keys():
            transcriber_tool = self.__di.tool_choice_resolver.require_tool(
                AudioTranscriber.TRANSCRIBER_TOOL_TYPE,
                AudioTranscriber.DEFAULT_TRANSCRIBER_TOOL,
            )
            copywriter_tool = self.__di.tool_choice_resolver.require_tool(
                AudioTranscriber.COPYWRITER_TOOL_TYPE,
                AudioTranscriber.DEFAULT_COPYWRITER_TOOL,
            )
            return self.__di.audio_transcriber(
                job_id = attachment.id,
                audio_url = attachment.last_url,
                transcriber_tool = transcriber_tool,
                copywriter_tool = copywriter_tool,
                def_extension = attachment.extension,
                audio_content = contents,
                language_name = self.__di.invoker_chat.language_name,
                language_iso_code = self.__di.invoker_chat.language_iso_code,
            ).execute()

        # handle documents
        if attachment.mime_type in KNOWN_DOCS_FORMATS.values() or attachment.extension in KNOWN_DOCS_FORMATS.keys():
            embedding_tool = self.__di.tool_choice_resolver.require_tool(
                DocumentSearch.EMBEDDING_TOOL_TYPE,
                DocumentSearch.DEFAULT_EMBEDDING_TOOL,
            )
            copywriter_tool = self.__di.tool_choice_resolver.require_tool(
                DocumentSearch.COPYWRITER_TOOL_TYPE,
                DocumentSearch.DEFAULT_COPYWRITER_TOOL,
            )
            return self.__di.document_search(
                job_id = attachment.id,
                document_url = attachment.last_url,
                embedding_tool = embedding_tool,
                copywriter_tool = copywriter_tool,
                additional_context = self.__additional_context,
            ).execute()

        self.sprint(f"Unsupported attachment '{attachment.id}': {attachment.mime_type}; '.{attachment.extension}'")
        return None
