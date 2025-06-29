from enum import Enum
from uuid import UUID

from db.crud.chat_message_attachment import ChatMessageAttachmentCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.schema.chat_message_attachment import ChatMessageAttachment
from db.schema.user import User
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.chat.telegram.sdk.telegram_bot_sdk_utils import TelegramBotSDKUtils
from features.external_tools.access_token_resolver import AccessTokenResolver
from features.images.image_background_remover import ImageBackgroundRemover
from features.images.image_contents_restorer import ImageContentsRestorer
from features.images.image_editor import ImageEditor
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


class ImageEditManager(SafePrinterMixin):
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
            return [op.value for op in ImageEditManager.Operation]

        @staticmethod
        def resolve(operation: str) -> "ImageEditManager.Operation":
            for op in ImageEditManager.Operation:
                if operation == op.value:
                    return op
            raise ValueError(f"Unknown operation '{operation}'")

    __chat_id: str
    __attachments: list[ChatMessageAttachment]
    __operation: Operation
    __operation_guidance: str | None
    __bot_sdk: TelegramBotSDK
    __invoker_user: User
    __user_dao: UserCRUD
    __chat_message_attachment_dao: ChatMessageAttachmentCRUD
    __token_resolver: AccessTokenResolver

    def __init__(
        self,
        chat_id: str,
        attachment_ids: list[str],
        invoker_user_id_hex: str,
        operation_name: str,
        bot_sdk: TelegramBotSDK,
        user_dao: UserCRUD,
        chat_message_attachment_dao: ChatMessageAttachmentCRUD,
        sponsorship_dao: SponsorshipCRUD,
        operation_guidance: str | None = None,
    ):
        super().__init__(config.verbose)
        self.__chat_id = chat_id
        self.__operation = ImageEditManager.Operation.resolve(operation_name)
        self.__operation_guidance = operation_guidance
        self.__bot_sdk = bot_sdk
        self.__user_dao = user_dao
        self.__chat_message_attachment_dao = chat_message_attachment_dao

        self.__validate(invoker_user_id_hex)
        self.__token_resolver = AccessTokenResolver(
            invoker_user = self.__invoker_user,
            user_dao = user_dao,
            sponsorship_dao = sponsorship_dao,
        )

        self.__attachments = TelegramBotSDKUtils.refresh_attachments(
            sources = attachment_ids,
            bot_api = bot_sdk.api,
            chat_message_attachment_dao = chat_message_attachment_dao,
        )

    def __validate(self, invoker_user_id_hex: str):
        self.sprint("Validating invoker data")
        invoker_user_db = self.__user_dao.get(UUID(hex = invoker_user_id_hex))
        if not invoker_user_db:
            message = f"Invoker '{invoker_user_id_hex}' not found"
            self.sprint(message)
            raise ValueError(message)
        self.__invoker_user = User.model_validate(invoker_user_db)

    def __remove_background(self) -> tuple[Result, list[str]]:
        self.sprint(f"Removing background from {len(self.__attachments)} images")
        result = ImageEditManager.Result.success
        urls: list[str] = []
        for attachment in self.__attachments:
            try:
                if not attachment.last_url:
                    self.sprint(f"Attachment '{attachment.id}' has no URL, skipping")
                    result = ImageEditManager.Result.partial
                    continue
                replicate_token = self.__token_resolver.require_access_token_for_tool(ImageBackgroundRemover.get_tool())
                remover = ImageBackgroundRemover(
                    image_url = attachment.last_url,
                    mime_type = attachment.mime_type,
                    replicate_api_key = replicate_token,
                )
                image_url = remover.execute()
                if not image_url:
                    self.sprint(f"Failed to remove background from attachment '{attachment.id}'")
                    result = ImageEditManager.Result.partial
                    continue
                self.sprint(f"Background removed from attachment '{attachment.id}'")
                urls.append(image_url)
            except Exception as e:
                self.sprint(f"Failed to remove background from attachment '{attachment.id}'", e)
                result = ImageEditManager.Result.partial
        if not urls:
            self.sprint("Failed to remove background from all images")
            result = ImageEditManager.Result.failed
        return result, urls

    def __restore_image(self) -> tuple[Result, list[str]]:
        self.sprint(f"Restoring {len(self.__attachments)} images")
        result = ImageEditManager.Result.success
        urls: list[str] = []
        for attachment in self.__attachments:
            try:
                if not attachment.last_url:
                    self.sprint(f"Attachment '{attachment.id}' has no URL, skipping")
                    result = ImageEditManager.Result.partial
                    continue
                self.__token_resolver.require_access_token_for_tool(ImageContentsRestorer.get_resoration_tool())
                replicate_token = self.__token_resolver.require_access_token_for_tool(
                    ImageContentsRestorer.get_inpainting_tool(),
                )
                remover = ImageContentsRestorer(
                    image_url = attachment.last_url,
                    mime_type = attachment.mime_type,
                    replicate_api_key = replicate_token,
                    # prompts could be added for better accuracy (class supports it)
                )
                restoration_result = remover.execute()
                if not restoration_result.restored_url and not restoration_result.inpainted_url:
                    self.sprint(f"Failed to restore image from attachment '{attachment.id}'")
                    result = ImageEditManager.Result.partial
                    continue
                self.sprint(f"Image from attachment '{attachment.id}' restored")
                if restoration_result.restored_url:
                    urls.append(restoration_result.restored_url)
                if restoration_result.inpainted_url:
                    urls.append(restoration_result.inpainted_url)
            except Exception as e:
                self.sprint(f"Failed to restore image from attachment '{attachment.id}'", e)
                result = ImageEditManager.Result.partial
        if not urls:
            self.sprint("Failed to restore all images")
            result = ImageEditManager.Result.failed
        return result, urls

    def __edit_image(self) -> tuple[Result, list[str]]:
        self.sprint(f"Editing {len(self.__attachments)} images")
        result = ImageEditManager.Result.success
        urls: list[str] = []
        for attachment in self.__attachments:
            try:
                if not attachment.last_url:
                    self.sprint(f"Attachment '{attachment.id}' has no URL, skipping")
                    result = ImageEditManager.Result.partial
                    continue
                replicate_token = self.__token_resolver.require_access_token_for_tool(ImageEditor.get_tool())
                editor = ImageEditor(
                    image_url = attachment.last_url,
                    replicate_api_key = replicate_token,
                    context = self.__operation_guidance,
                    mime_type = attachment.mime_type,
                )
                editing_result = editor.execute()
                if not editing_result:
                    self.sprint(f"Failed to edit image from attachment '{attachment.id}'")
                    result = ImageEditManager.Result.partial
                    continue
                self.sprint(f"Image from attachment '{attachment.id}' was edited")
                urls.append(editing_result)
            except Exception as e:
                self.sprint(f"Failed to edit image from attachment '{attachment.id}'", e)
                result = ImageEditManager.Result.partial
        if not urls:
            self.sprint("Failed to restore all images")
            result = ImageEditManager.Result.failed
        return result, urls

    def execute(self) -> tuple[Result, dict[str, int]]:
        self.sprint(f"Editing images for chat '{self.__chat_id}', operation '{self.__operation.value}'")

        if self.__operation == ImageEditManager.Operation.remove_background:
            result, urls = self.__remove_background()
            urls = self.__clean_urls(urls)
            for image_url in urls:
                self.sprint(f"Sending edited image to chat '{self.__chat_id}'")
                self.__bot_sdk.send_document(self.__chat_id, image_url, thumbnail = image_url)
                self.sprint("Image edited and sent successfully")
            return result, {"image_backgrounds_removed": len(urls)}

        elif self.__operation == ImageEditManager.Operation.restore_image:
            result, urls = self.__restore_image()
            urls = self.__clean_urls(urls)
            for image_url in urls:
                self.sprint(f"Sending restored image to chat '{self.__chat_id}': {image_url}")
                self.__bot_sdk.send_document(self.__chat_id, image_url, thumbnail = image_url)
                self.sprint("Image restored and sent successfully")
            return result, {"images_restored": len(urls)}

        elif self.__operation == ImageEditManager.Operation.edit_image:
            result, urls = self.__edit_image()
            urls = self.__clean_urls(urls)
            for image_url in urls:
                self.sprint(f"Sending edited image to chat '{self.__chat_id}': {image_url}")
                self.__bot_sdk.send_photo(self.__chat_id, image_url)
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
