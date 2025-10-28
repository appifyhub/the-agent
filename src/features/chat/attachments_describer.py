import base64
from datetime import datetime, timedelta
from enum import Enum

import requests

from db.schema.chat_message_attachment import ChatMessageAttachment
from db.schema.tools_cache import ToolsCache, ToolsCacheSave
from di.di import DI
from features.audio.audio_transcriber import AudioTranscriber
from features.chat.supported_files import KNOWN_AUDIO_FORMATS, KNOWN_DOCS_FORMATS, KNOWN_IMAGE_FORMATS
from features.documents.document_search import DocumentSearch
from features.images.computer_vision_analyzer import ComputerVisionAnalyzer
from util import log
from util.functions import digest_md5

CACHE_PREFIX = "attachments-describer"
CACHE_TTL = timedelta(weeks = 13)


class AttachmentsDescriber:

    class Result(Enum):
        failed = "Failed"
        partial = "Partial"
        success = "Success"

    # the following two lists are in sync
    __attachments: list[ChatMessageAttachment]
    __contents: list[str | None]
    __errors: list[str | None]

    __additional_context: str | None
    __di: DI

    def __init__(
        self,
        additional_context: str | None,
        attachment_ids: list[str],
        di: DI,
    ):
        self.__attachments = []
        self.__contents = []
        self.__errors = []
        self.__additional_context = additional_context
        self.__di = di
        self.__validate(attachment_ids)

    def __validate(self, attachment_ids: list[str]) -> None:
        log.d(f"Validating {len(attachment_ids)} attachments in chat '{self.__di.invoker_chat_id}'")
        if not attachment_ids:
            raise ValueError(log.d("Malformed LLM Input Error: No attachment IDs provided. You may retry only once!"))
        attachments: list[ChatMessageAttachment] = []
        for attachment_id in attachment_ids:
            if not attachment_id:
                raise ValueError(log.d("Malformed LLM Input Error: Attachment ID cannot be empty. You may retry only once!"))
            attachment_db = self.__di.chat_message_attachment_crud.get(attachment_id)
            if not attachment_db:
                raise ValueError(
                    log.d(f"Malformed LLM Input Error: Attachment '{attachment_id}' not found in DB. You may retry only once!"),
                )
            attachments.append(ChatMessageAttachment.model_validate(attachment_db))
        self.__attachments = self.__di.platform_bot_sdk().refresh_attachment_instances(attachments)

    @property
    def __resolution_status(self) -> Result:
        if not self.__attachments:
            return AttachmentsDescriber.Result.failed
        contents_match_attachments = len(self.__attachments) == len(self.__contents)
        # failure -> attachments don't match contents (system error)
        if not contents_match_attachments:
            return AttachmentsDescriber.Result.failed
        successful_contents = sum(1 for content in self.__contents if content is not None)
        # failure -> 0% success (no content resolved)
        if successful_contents == 0:
            return AttachmentsDescriber.Result.failed
        # success -> 100% success (all content resolved)
        if successful_contents == len(self.__attachments):
            return AttachmentsDescriber.Result.success
        # partial -> some content resolved, some failed
        return AttachmentsDescriber.Result.partial

    @property
    def result(self) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        for attachment, content, error in zip(self.__attachments, self.__contents, self.__errors):
            attachment_data = {
                "id": attachment.id,
                "text_content": content if content is not None else "<unresolved>",
                "type": attachment.mime_type if attachment.mime_type else "<unknown>",
                "error": error if error else "<none>",
            }
            result.append(attachment_data)
        return result

    def execute(self) -> Result:
        log.d("Resolving attachments content")

        self.__contents = []
        self.__errors = []
        for attachment in self.__attachments:
            # assuming the URL will never change... users might ask more questions about the same attachment
            additional_content_hash = digest_md5(self.__additional_context) if self.__additional_context else "*"
            unique_identifier = f"{attachment.id}-{additional_content_hash}"
            cache_key = self.__di.tools_cache_crud.create_key(CACHE_PREFIX, unique_identifier)
            cache_entry_db = self.__di.tools_cache_crud.get(cache_key)
            if cache_entry_db:
                cache_entry = ToolsCache.model_validate(cache_entry_db)
                if not cache_entry.is_expired():
                    log.t(f"Cache hit for '{cache_key}'")
                    self.__contents.append(cache_entry.value)
                    self.__errors.append(None)
                    continue
                log.t(f"Cache expired for '{cache_key}'")
            log.t(f"Cache miss for '{cache_key}'")
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
                self.__errors.append(None)
            except Exception as e:
                self.__contents.append(None)
                self.__errors.append(log.w(f"Error resolving contents for '{attachment.id}'", e))

        result = self.__resolution_status
        log.i(f"Resolution result: {result}")
        return result

    def fetch_text_content(self, attachment: ChatMessageAttachment) -> str | None:
        log.t(f"Resolving text content for attachment '{attachment.id}'")

        # fetching binary contents will also validate the URL
        contents = requests.get(str(attachment.last_url)).content

        # handle images
        if attachment.mime_type in KNOWN_IMAGE_FORMATS.values() or attachment.extension in KNOWN_IMAGE_FORMATS.keys():
            configured_tool = self.__di.tool_choice_resolver.require_tool(
                ComputerVisionAnalyzer.TOOL_TYPE,
                ComputerVisionAnalyzer.DEFAULT_TOOL,
            )
            return self.__di.computer_vision_analyzer(
                job_id = attachment.id,
                image_mime_type = str(attachment.mime_type),
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
                audio_url = str(attachment.last_url),
                transcriber_tool = transcriber_tool,
                copywriter_tool = copywriter_tool,
                def_extension = attachment.extension,
                audio_content = contents,
                language_name = self.__di.require_invoker_chat().language_name,
                language_iso_code = self.__di.require_invoker_chat().language_iso_code,
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
                document_url = str(attachment.last_url),
                embedding_tool = embedding_tool,
                copywriter_tool = copywriter_tool,
                additional_context = self.__additional_context,
            ).execute()

        log.w(f"Unsupported attachment '{attachment.id}': {attachment.mime_type}; '.{attachment.extension}'")
        return None
