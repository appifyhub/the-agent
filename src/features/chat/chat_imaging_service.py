from enum import Enum

from db.schema.chat_message_attachment import ChatMessageAttachment
from di.di import DI
from features.images.image_background_remover import ImageBackgroundRemover
from features.images.image_contents_restorer import ImageContentsRestorer
from features.images.image_editor import ImageEditor
from util import log

URLList = list[str | None]
ErrorList = list[str | None]


class ChatImagingService:

    class Result(Enum):
        success = "success"
        failed = "failed"
        partial = "partial"

    class Operation(Enum):
        remove_background = "remove-background"
        restore_image = "restore-image"
        edit_image = "edit-image"

        @staticmethod
        def values():
            return [op.value for op in ChatImagingService.Operation]

        @staticmethod
        def resolve(operation: str) -> "ChatImagingService.Operation":
            for op in ChatImagingService.Operation:
                if operation == op.value:
                    return op
            raise ValueError(f"Unknown operation '{operation}'")

    __attachments: list[ChatMessageAttachment]
    __operation: Operation
    __operation_guidance: str | None
    __di: DI

    def __init__(
        self,
        attachment_ids: list[str],
        operation_name: str,
        operation_guidance: str | None,
        di: DI,
    ):
        if not attachment_ids:
            raise ValueError("No attachment IDs provided")
        self.__di = di
        self.__attachments = self.__di.telegram_bot_sdk.refresh_attachments_by_ids(attachment_ids)
        self.__operation = ChatImagingService.Operation.resolve(operation_name)
        self.__operation_guidance = operation_guidance

    def __remove_background(self) -> tuple[Result, URLList, ErrorList]:
        log.t(f"Removing background from {len(self.__attachments)} images")
        result = ChatImagingService.Result.success
        urls: URLList = []
        errors: ErrorList = []
        for attachment in self.__attachments:
            try:
                if not attachment.last_url:
                    urls.append(None)
                    errors.append(log.w(f"Attachment '{attachment.id}' has no URL, skipping"))
                    result = ChatImagingService.Result.partial
                    continue
                configured_tool = self.__di.tool_choice_resolver.require_tool(
                    ImageBackgroundRemover.TOOL_TYPE,
                    ImageBackgroundRemover.DEFAULT_TOOL,
                )
                remover = self.__di.image_background_remover(
                    image_url = attachment.last_url,
                    configured_tool = configured_tool,
                    mime_type = attachment.mime_type,
                )
                image_url = remover.execute()
                if remover.error:
                    urls.append(None)
                    errors.append(log.w(f"Error removing background from attachment '{attachment.id}': {remover.error}"))
                    result = ChatImagingService.Result.partial
                    continue
                if not image_url:
                    urls.append(None)
                    errors.append(log.w(f"Background was not removed from attachment '{attachment.id}'"))
                    result = ChatImagingService.Result.partial
                    continue
                log.t(f"Background removed from attachment '{attachment.id}'!")
                urls.append(image_url)
                errors.append(None)
            except Exception as e:
                urls.append(None)
                errors.append(log.w(f"Failed to remove background from attachment '{attachment.id}'", e))
                result = ChatImagingService.Result.partial
        # set the correct error state if no URLs were returned
        if not urls or all(url is None for url in urls):
            log.w("Failed to remove background from all images")
            result = ChatImagingService.Result.failed
        return result, urls, errors

    def __restore_image(self) -> tuple[Result, URLList, ErrorList]:
        log.t(f"Restoring {len(self.__attachments)} images")
        result = ChatImagingService.Result.success
        urls: URLList = []
        errors: ErrorList = []
        for attachment in self.__attachments:
            try:
                if not attachment.last_url:
                    urls.append(None)
                    errors.append(log.w(f"Attachment '{attachment.id}' has no URL, skipping"))
                    result = ChatImagingService.Result.partial
                    continue
                restoration_tool = self.__di.tool_choice_resolver.require_tool(
                    ImageContentsRestorer.RESTORATION_TOOL_TYPE,
                    ImageContentsRestorer.DEFAULT_RESTORATION_TOOL,
                )
                inpainting_tool = self.__di.tool_choice_resolver.require_tool(
                    ImageContentsRestorer.INPAINTING_TOOL_TYPE,
                    ImageContentsRestorer.DEFAULT_INPAINTING_TOOL,
                )
                restorer = self.__di.image_contents_restorer(
                    image_url = attachment.last_url,
                    mime_type = attachment.mime_type,
                    restoration_tool = restoration_tool,
                    inpainting_tool = inpainting_tool,
                    # prompts could be added for better accuracy (class supports it)
                )
                restoration_result = restorer.execute()
                if not restoration_result.restored_url and not restoration_result.inpainted_url:
                    urls.append(None)
                    errors.append(
                        log.w(f"Failed to restore image from attachment '{attachment.id}', error: {restoration_result.error}"),
                    )
                    result = ChatImagingService.Result.partial
                    continue
                log.t(f"Image from attachment '{attachment.id}' restored!")
                urls.append(restoration_result.inpainted_url or restoration_result.restored_url or None)
                errors.append(restoration_result.error)
            except Exception as e:
                urls.append(None)
                errors.append(log.w(f"Failed to restore image from attachment '{attachment.id}'", e))
                result = ChatImagingService.Result.partial
        if not urls or all(url is None for url in urls):
            log.w("Failed to restore all images")
            result = ChatImagingService.Result.failed
        return result, urls, errors

    def __edit_image(self) -> tuple[Result, URLList, ErrorList]:
        log.t(f"Editing {len(self.__attachments)} images")
        result = ChatImagingService.Result.success
        urls: URLList = []
        errors: ErrorList = []
        for attachment in self.__attachments:
            try:
                if not attachment.last_url:
                    urls.append(None)
                    errors.append(log.w(f"Attachment '{attachment.id}' has no URL, skipping"))
                    result = ChatImagingService.Result.partial
                    continue
                configured_tool = self.__di.tool_choice_resolver.require_tool(ImageEditor.TOOL_TYPE, ImageEditor.DEFAULT_TOOL)
                editor = self.__di.image_editor(
                    image_url = attachment.last_url,
                    configured_tool = configured_tool,
                    context = self.__operation_guidance,
                    mime_type = attachment.mime_type,
                )
                editing_result = editor.execute()
                if editor.error:
                    urls.append(None)
                    errors.append(log.w(f"Error editing image from attachment '{attachment.id}': {editor.error}"))
                    result = ChatImagingService.Result.partial
                    continue
                if not editing_result:
                    urls.append(None)
                    errors.append(log.w(f"Failed to edit image from attachment '{attachment.id}'"))
                    result = ChatImagingService.Result.partial
                    continue
                log.t(f"Image from attachment '{attachment.id}' was edited!")
                urls.append(editing_result)
                errors.append(None)
            except Exception as e:
                urls.append(None)
                errors.append(log.w(f"Failed to edit image from attachment '{attachment.id}'", e))
                result = ChatImagingService.Result.partial
        if not urls or all(url is None for url in urls):
            log.w("Failed to edit all images")
            result = ChatImagingService.Result.failed
        return result, urls, errors

    def execute(self) -> tuple[Result, list[dict[str, str | None]]]:
        invoker_chat = self.__di.require_invoker_chat()
        log.t(f"Editing images for chat '{invoker_chat.chat_id}', operation '{self.__operation.value}'")

        if self.__operation == ChatImagingService.Operation.remove_background:
            result, urls, errors = self.__remove_background()
            urls = self.__clean_urls(urls)
            output: list[dict[str, str | None]] = []
            for image_url, error in zip(urls, errors):
                if image_url is None:
                    output.append({"url": None, "error": error})
                    continue
                external_id = str(invoker_chat.external_id)
                log.t(f"Sending edited image to chat '{external_id}'")
                self.__di.telegram_bot_sdk.send_document(external_id, image_url, thumbnail = image_url)
                self.__di.telegram_bot_sdk.send_photo(external_id, image_url, caption = "📸")
                log.t("Image edited and sent successfully")
                output.append({"url": image_url, "error": None, "status": "delivered"})
            return result, output

        elif self.__operation == ChatImagingService.Operation.restore_image:
            result, urls, errors = self.__restore_image()
            urls = self.__clean_urls(urls)
            output: list[dict[str, str | None]] = []
            for image_url, error in zip(urls, errors):
                if image_url is None:
                    output.append({"url": None, "error": error})
                    continue
                external_id = str(invoker_chat.external_id)
                log.t(f"Sending restored image to chat '{external_id}': {image_url}")
                self.__di.telegram_bot_sdk.send_document(external_id, image_url, thumbnail = image_url)
                self.__di.telegram_bot_sdk.send_photo(external_id, image_url, caption = "📸")
                log.t("Image restored and sent successfully")
                output.append({"url": image_url, "error": None, "status": "delivered"})
            return result, output

        elif self.__operation == ChatImagingService.Operation.edit_image:
            result, urls, errors = self.__edit_image()
            urls = self.__clean_urls(urls)
            output: list[dict[str, str | None]] = []
            for image_url, error in zip(urls, errors):
                if image_url is None:
                    output.append({"url": None, "error": error})
                    continue
                external_id = str(invoker_chat.external_id)
                log.t(f"Sending edited image to chat '{external_id}': {image_url}")
                self.__di.telegram_bot_sdk.send_document(external_id, image_url, thumbnail = image_url)
                self.__di.telegram_bot_sdk.send_photo(external_id, image_url, caption = "📸")
                log.t("Image edited and sent successfully")
                output.append({"url": image_url, "error": None, "status": "delivered"})
            return result, output

        else:
            raise ValueError(f"Unknown operation '{self.__operation.value}'")

    @staticmethod  # why? because python has no real types
    def __clean_urls(urls: list) -> URLList:
        result: list = []
        for url in urls:
            if isinstance(url, list):
                if url and isinstance(url[0], str):
                    result.append(url[0])
                continue
            elif isinstance(url, str):
                result.append(url)
            elif url is not None:
                result.append(str(url))
            else:
                result.append(None)
            continue
        return result
