from enum import Enum

from db.schema.chat_message_attachment import ChatMessageAttachment
from di.di import DI
from features.chat.telegram.sdk.telegram_bot_sdk_utils import TelegramBotSDKUtils
from features.images.image_background_remover import ImageBackgroundRemover
from features.images.image_contents_restorer import ImageContentsRestorer
from features.images.image_editor import ImageEditor
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


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
        self.__di = di
        self.__attachments = TelegramBotSDKUtils.refresh_attachments(
            sources = attachment_ids,
            bot_api = self.__di.telegram_bot_api,
            chat_message_attachment_dao = self.__di.chat_message_attachment_crud,
        )
        self.__operation = ChatImagingService.Operation.resolve(operation_name)
        self.__operation_guidance = operation_guidance

    def __remove_background(self) -> tuple[Result, list[str]]:
        self.sprint(f"Removing background from {len(self.__attachments)} images")
        result = ChatImagingService.Result.success
        urls: list[str] = []
        for attachment in self.__attachments:
            try:
                if not attachment.last_url:
                    self.sprint(f"Attachment '{attachment.id}' has no URL, skipping")
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
                if not image_url:
                    self.sprint(f"Failed to remove background from attachment '{attachment.id}'")
                    result = ChatImagingService.Result.partial
                    continue
                self.sprint(f"Background removed from attachment '{attachment.id}'")
                urls.append(image_url)
            except Exception as e:
                self.sprint(f"Failed to remove background from attachment '{attachment.id}'", e)
                result = ChatImagingService.Result.partial
        if not urls:
            self.sprint("Failed to remove background from all images")
            result = ChatImagingService.Result.failed
        return result, urls

    def __restore_image(self) -> tuple[Result, list[str]]:
        self.sprint(f"Restoring {len(self.__attachments)} images")
        result = ChatImagingService.Result.success
        urls: list[str] = []
        for attachment in self.__attachments:
            try:
                if not attachment.last_url:
                    self.sprint(f"Attachment '{attachment.id}' has no URL, skipping")
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
                remover = self.__di.image_contents_restorer(
                    image_url = attachment.last_url,
                    mime_type = attachment.mime_type,
                    restoration_tool = restoration_tool,
                    inpainting_tool = inpainting_tool,
                    # prompts could be added for better accuracy (class supports it)
                )
                restoration_result = remover.execute()
                if not restoration_result.restored_url and not restoration_result.inpainted_url:
                    self.sprint(f"Failed to restore image from attachment '{attachment.id}'")
                    result = ChatImagingService.Result.partial
                    continue
                self.sprint(f"Image from attachment '{attachment.id}' restored")
                if restoration_result.restored_url:
                    urls.append(restoration_result.restored_url)
                if restoration_result.inpainted_url:
                    urls.append(restoration_result.inpainted_url)
            except Exception as e:
                self.sprint(f"Failed to restore image from attachment '{attachment.id}'", e)
                result = ChatImagingService.Result.partial
        if not urls:
            self.sprint("Failed to restore all images")
            result = ChatImagingService.Result.failed
        return result, urls

    def __edit_image(self) -> tuple[Result, list[str]]:
        self.sprint(f"Editing {len(self.__attachments)} images")
        result = ChatImagingService.Result.success
        urls: list[str] = []
        for attachment in self.__attachments:
            try:
                if not attachment.last_url:
                    self.sprint(f"Attachment '{attachment.id}' has no URL, skipping")
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
                if not editing_result:
                    self.sprint(f"Failed to edit image from attachment '{attachment.id}'")
                    result = ChatImagingService.Result.partial
                    continue
                self.sprint(f"Image from attachment '{attachment.id}' was edited")
                urls.append(editing_result)
            except Exception as e:
                self.sprint(f"Failed to edit image from attachment '{attachment.id}'", e)
                result = ChatImagingService.Result.partial
        if not urls:
            self.sprint("Failed to restore all images")
            result = ChatImagingService.Result.failed
        return result, urls

    def execute(self) -> tuple[Result, dict[str, int]]:
        self.sprint(f"Editing images for chat '{self.__di.invoker_chat.chat_id}', operation '{self.__operation.value}'")

        if self.__operation == ChatImagingService.Operation.remove_background:
            result, urls = self.__remove_background()
            urls = self.__clean_urls(urls)
            for image_url in urls:
                self.sprint(f"Sending edited image to chat '{self.__di.invoker_chat.chat_id}'")
                self.__di.telegram_bot_sdk.send_document(self.__di.invoker_chat.chat_id, image_url, thumbnail = image_url)
                self.sprint("Image edited and sent successfully")
            return result, {"image_backgrounds_removed": len(urls)}

        elif self.__operation == ChatImagingService.Operation.restore_image:
            result, urls = self.__restore_image()
            urls = self.__clean_urls(urls)
            for image_url in urls:
                self.sprint(f"Sending restored image to chat '{self.__di.invoker_chat.chat_id}': {image_url}")
                self.__di.telegram_bot_sdk.send_document(self.__di.invoker_chat.chat_id, image_url, thumbnail = image_url)
                self.sprint("Image restored and sent successfully")
            return result, {"images_restored": len(urls)}

        elif self.__operation == ChatImagingService.Operation.edit_image:
            result, urls = self.__edit_image()
            urls = self.__clean_urls(urls)
            for image_url in urls:
                self.sprint(f"Sending edited image to chat '{self.__di.invoker_chat.chat_id}': {image_url}")
                self.__di.telegram_bot_sdk.send_photo(self.__di.invoker_chat.chat_id, image_url)
                self.sprint("Image edited and sent successfully")
            return result, {"images_edited": len(urls)}

        else:
            raise ValueError(f"Unknown operation '{self.__operation.value}'")

    @staticmethod
    def __clean_urls(urls: list) -> list:
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
            continue
        return result
