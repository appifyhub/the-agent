from enum import Enum

from db.schema.chat_message_attachment import ChatMessageAttachment
from di.di import DI
from features.images.image_editor import ImageEditor
from util import log

URLList = list[str | None]
ErrorList = list[str | None]


class ChatImageEditService:

    class Result(Enum):
        success = "success"
        failed = "failed"
        partial = "partial"

    __attachments: list[ChatMessageAttachment]
    __operation_guidance: str | None
    __aspect_ratio: str | None
    __output_size: str | None
    __di: DI

    def __init__(
        self,
        attachment_ids: list[str],
        operation_guidance: str | None,
        aspect_ratio: str | None,
        output_size: str | None,
        di: DI,
    ):
        if not attachment_ids:
            raise ValueError("No attachment IDs provided")
        self.__di = di
        self.__attachments = self.__di.platform_bot_sdk().refresh_attachments_by_ids(attachment_ids)
        self.__operation_guidance = operation_guidance
        self.__aspect_ratio = aspect_ratio
        self.__output_size = output_size

    def __edit_image(self) -> tuple[Result, URLList, ErrorList]:
        log.t(f"Editing {len(self.__attachments)} images in aspect ratio {self.__aspect_ratio}")
        result = ChatImageEditService.Result.success
        urls: URLList = []
        errors: ErrorList = []
        for attachment in self.__attachments:
            try:
                if not attachment.last_url:
                    urls.append(None)
                    errors.append(log.w(f"Attachment '{attachment.id}' has no URL, skipping"))
                    result = ChatImageEditService.Result.partial
                    continue
                configured_tool = self.__di.tool_choice_resolver.require_tool(ImageEditor.TOOL_TYPE, ImageEditor.DEFAULT_TOOL)
                editor = self.__di.image_editor(
                    image_url = attachment.last_url,
                    configured_tool = configured_tool,
                    prompt = self.__operation_guidance or "<empty>",
                    input_mime_type = attachment.mime_type,
                    aspect_ratio = self.__aspect_ratio,
                    output_size = self.__output_size,
                )
                editing_result = editor.execute()
                if editor.error:
                    urls.append(None)
                    errors.append(log.w(f"Error editing image from attachment '{attachment.id}': {editor.error}"))
                    result = ChatImageEditService.Result.partial
                    continue
                if not editing_result:
                    urls.append(None)
                    errors.append(log.w(f"Failed to edit image from attachment '{attachment.id}'"))
                    result = ChatImageEditService.Result.partial
                    continue
                log.t(f"Image from attachment '{attachment.id}' was edited!")
                urls.append(editing_result)
                errors.append(None)
            except Exception as e:
                urls.append(None)
                errors.append(log.w(f"Failed to edit image from attachment '{attachment.id}'", e))
                result = ChatImageEditService.Result.partial
        if not urls or all(url is None for url in urls):
            log.w("Failed to edit all images")
            result = ChatImageEditService.Result.failed
        return result, urls, errors

    def execute(self) -> tuple[Result, list[dict[str, str | None]]]:
        invoker_chat = self.__di.require_invoker_chat()
        log.t(f"Editing images for chat '{invoker_chat.chat_id}'")

        result, urls, errors = self.__edit_image()
        urls = self.__clean_urls(urls)
        output_editing_urls: list[dict[str, str | None]] = []
        for image_url, error in zip(urls, errors):
            if image_url is None:
                output_editing_urls.append({"url": None, "error": error})
                continue
            external_id = str(invoker_chat.external_id)
            log.t(f"Sending edited image to chat '{external_id}': {image_url}")
            self.__di.platform_bot_sdk().smart_send_photo(
                media_mode = invoker_chat.media_mode,
                chat_id = external_id,
                photo_url = image_url,
                caption = "📸",
                thumbnail = image_url,
            )
            log.t("Image edited and sent successfully")
            output_editing_urls.append({"url": image_url, "error": None, "status": "delivered"})
        return result, output_editing_urls

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
