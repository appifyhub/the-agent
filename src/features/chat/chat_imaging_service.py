from enum import Enum

from db.schema.chat_message_attachment import ChatMessageAttachment
from di.di import DI
from features.chat.telegram.sdk.telegram_bot_sdk_utils import TelegramBotSDKUtils
from features.images.image_background_remover import ImageBackgroundRemover
from features.images.image_contents_restorer import ImageContentsRestorer
from features.images.image_editor import ImageEditor
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

URLList = list[str | None]
ErrorList = list[str | None]


class ChatImagingService(SafePrinterMixin):
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
        super().__init__(config.verbose)
        if not attachment_ids:
            raise ValueError("No attachment IDs provided")
        self.__di = di
        self.__attachments = TelegramBotSDKUtils.refresh_attachments_by_ids(self.__di, attachment_ids)
        self.__operation = ChatImagingService.Operation.resolve(operation_name)
        self.__operation_guidance = operation_guidance

    def __remove_background(self) -> tuple[Result, URLList, ErrorList]:
        self.sprint(f"Removing background from {len(self.__attachments)} images")
        result = ChatImagingService.Result.success
        urls: URLList = []
        errors: ErrorList = []
        for attachment in self.__attachments:
            try:
                if not attachment.last_url:
                    self.sprint(f"Attachment '{attachment.id}' has no URL, skipping")
                    urls.append(None)
                    errors.append("Attachment has no URL")
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
                    self.sprint(f"Error removing background from attachment '{attachment.id}': {remover.error}")
                    urls.append(None)
                    errors.append(remover.error)
                    result = ChatImagingService.Result.partial
                    continue
                if not image_url:
                    self.sprint(f"Background was not removed from attachment '{attachment.id}'")
                    urls.append(None)
                    errors.append(remover.error)
                    result = ChatImagingService.Result.partial
                    continue
                self.sprint(f"Background removed from attachment '{attachment.id}'!")
                urls.append(image_url)
                errors.append(None)
            except Exception as e:
                self.sprint(f"Failed to remove background from attachment '{attachment.id}'", e)
                urls.append(None)
                errors.append(str(e))
                result = ChatImagingService.Result.partial
        # set the correct error state if no URLs were returned
        if not urls or all(url is None for url in urls):
            self.sprint("Failed to remove background from all images")
            result = ChatImagingService.Result.failed
        return result, urls, errors

    def __restore_image(self) -> tuple[Result, URLList, ErrorList]:
        self.sprint(f"Restoring {len(self.__attachments)} images")
        result = ChatImagingService.Result.success
        urls: URLList = []
        errors: ErrorList = []
        for attachment in self.__attachments:
            try:
                if not attachment.last_url:
                    self.sprint(f"Attachment '{attachment.id}' has no URL, skipping")
                    urls.append(None)
                    errors.append("Attachment has no URL")
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
                    self.sprint(f"Failed to restore image from attachment '{attachment.id}'")
                    urls.append(None)
                    errors.append(restoration_result.error)
                    result = ChatImagingService.Result.partial
                    continue
                self.sprint(f"Image from attachment '{attachment.id}' restored!")
                urls.append(restoration_result.inpainted_url or restoration_result.restored_url or None)
                errors.append(restoration_result.error)
            except Exception as e:
                self.sprint(f"Failed to restore image from attachment '{attachment.id}'", e)
                urls.append(None)
                errors.append(str(e))
                result = ChatImagingService.Result.partial
        if not urls or all(url is None for url in urls):
            self.sprint("Failed to restore all images")
            result = ChatImagingService.Result.failed
        return result, urls, errors

    def __edit_image(self) -> tuple[Result, URLList, ErrorList]:
        self.sprint(f"Editing {len(self.__attachments)} images")
        result = ChatImagingService.Result.success
        urls: URLList = []
        errors: ErrorList = []
        for attachment in self.__attachments:
            try:
                if not attachment.last_url:
                    self.sprint(f"Attachment '{attachment.id}' has no URL, skipping")
                    urls.append(None)
                    errors.append("Attachment has no URL")
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
                    self.sprint(f"Error editing image from attachment '{attachment.id}': {editor.error}")
                    urls.append(None)
                    errors.append(editor.error)
                    result = ChatImagingService.Result.partial
                    continue
                if not editing_result:
                    self.sprint(f"Failed to edit image from attachment '{attachment.id}'")
                    urls.append(None)
                    errors.append(editor.error)
                    result = ChatImagingService.Result.partial
                    continue
                self.sprint(f"Image from attachment '{attachment.id}' was edited!")
                urls.append(editing_result)
                errors.append(None)
            except Exception as e:
                self.sprint(f"Failed to edit image from attachment '{attachment.id}'", e)
                result = ChatImagingService.Result.partial
                urls.append(None)
                errors.append(str(e))
        if not urls or all(url is None for url in urls):
            self.sprint("Failed to edit all images")
            result = ChatImagingService.Result.failed
        return result, urls, errors

    def execute(self) -> tuple[Result, list[dict[str, str | None]]]:
        self.sprint(f"Editing images for chat '{self.__di.invoker_chat.chat_id}', operation '{self.__operation.value}'")

        if self.__operation == ChatImagingService.Operation.remove_background:
            result, urls, errors = self.__remove_background()
            urls = self.__clean_urls(urls)
            output: list[dict[str, str | None]] = []
            for image_url, error in zip(urls, errors):
                if image_url is None:
                    output.append({"url": None, "error": error})
                    continue
                self.sprint(f"Sending edited image to chat '{self.__di.invoker_chat.chat_id}'")
                self.__di.telegram_bot_sdk.send_document(self.__di.invoker_chat.chat_id, image_url, thumbnail = image_url)
                self.__di.telegram_bot_sdk.send_photo(self.__di.invoker_chat.chat_id, image_url, caption = "📸")
                self.sprint("Image edited and sent successfully")
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
                self.sprint(f"Sending restored image to chat '{self.__di.invoker_chat.chat_id}': {image_url}")
                self.__di.telegram_bot_sdk.send_document(self.__di.invoker_chat.chat_id, image_url, thumbnail = image_url)
                self.__di.telegram_bot_sdk.send_photo(self.__di.invoker_chat.chat_id, image_url, caption = "📸")
                self.sprint("Image restored and sent successfully")
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
                self.sprint(f"Sending edited image to chat '{self.__di.invoker_chat.chat_id}': {image_url}")
                self.__di.telegram_bot_sdk.send_document(self.__di.invoker_chat.chat_id, image_url, thumbnail = image_url)
                self.__di.telegram_bot_sdk.send_photo(self.__di.invoker_chat.chat_id, image_url, caption = "📸")
                self.sprint("Image edited and sent successfully")
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
