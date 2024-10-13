from datetime import datetime
from enum import Enum
from uuid import UUID

from db.crud.chat_message_attachment import ChatMessageAttachmentCRUD
from db.crud.user import UserCRUD
from db.model.user import UserDB
from db.schema.chat_message_attachment import ChatMessageAttachment
from db.schema.user import User
from features.chat.attachments_content_resolver import AttachmentsContentResolver
from features.chat.telegram.model.message import Message
from features.chat.telegram.model.update import Update
from features.chat.telegram.telegram_bot_api import TelegramBotAPI
from features.chat.telegram.telegram_data_resolver import TelegramDataResolver
from features.chat.telegram.telegram_domain_mapper import TelegramDomainMapper
from features.images.image_background_remover import ImageBackgroundRemover
from features.images.image_background_replacer import ImageBackgroundReplacer
from features.images.image_contents_restorer import ImageContentsRestorer
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


class ImageEditManager(SafePrinterMixin):
    class Result(Enum):
        success = "success"
        failed = "failed"
        partial = "partial"

    class Operation(Enum):
        remove_background = "remove-background"
        replace_background = "replace-background"
        restore_image = "restore-image"

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
    __bot_api: TelegramBotAPI
    __invoker_user: User
    __user_dao: UserCRUD
    __chat_message_attachment_dao: ChatMessageAttachmentCRUD

    def __init__(
        self,
        chat_id: str,
        attachment_ids: list[str],
        invoker_user_id_hex: str,
        operation_name: str,
        bot_api: TelegramBotAPI,
        user_dao: UserCRUD,
        chat_message_attachment_dao: ChatMessageAttachmentCRUD,
        operation_guidance: str | None = None,
    ):
        super().__init__(config.verbose)
        self.__chat_id = chat_id
        self.__operation = ImageEditManager.Operation.resolve(operation_name)
        self.__operation_guidance = operation_guidance
        self.__bot_api = bot_api
        self.__user_dao = user_dao
        self.__chat_message_attachment_dao = chat_message_attachment_dao
        self.__validate(invoker_user_id_hex)
        self.__attachments = AttachmentsContentResolver.refresh_attachment_files(
            attachment_ids, chat_message_attachment_dao, bot_api,
        )

    def __validate(self, invoker_user_id_hex: str):
        self.sprint("Validating invoker data")
        invoker_user_db = self.__user_dao.get(UUID(hex = invoker_user_id_hex))
        if not invoker_user_db:
            message = f"Invoker '{invoker_user_id_hex}' not found"
            self.sprint(message)
            raise ValueError(message)
        self.__invoker_user = User.model_validate(invoker_user_db)
        if self.__invoker_user.group < UserDB.Group.beta:
            message = f"Invoker '{invoker_user_id_hex}' is not allowed to edit images"
            self.sprint(message)
            raise ValueError(message)

    def __remove_background(self) -> tuple[Result, list[str]]:
        self.sprint(f"Removing background from {len(self.__attachments)} images")
        result = ImageEditManager.Result.success
        urls: list[str] = []
        for attachment in self.__attachments:
            try:
                remover = ImageBackgroundRemover(
                    image_url = attachment.last_url,
                    mime_type = attachment.mime_type,
                    replicate_api_key = config.replicate_api_token,
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
                remover = ImageContentsRestorer(
                    image_url = attachment.last_url,
                    mime_type = attachment.mime_type,
                    replicate_api_key = config.replicate_api_token,
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

    def __replace_background(self) -> tuple[Result, list[str]]:
        self.sprint(f"Replacing image background on {len(self.__attachments)} images")
        result = ImageEditManager.Result.success
        urls: list[str] = []
        for attachment in self.__attachments:
            try:
                remover = ImageBackgroundReplacer(
                    job_id = attachment.id,
                    image_url = attachment.last_url,
                    mime_type = attachment.mime_type,
                    change_request = self.__operation_guidance,
                    replicate_api_key = config.replicate_api_token,
                    anthropic_api_key = config.anthropic_token,
                    open_ai_api_key = config.open_ai_token,
                    how_many_variants = 1,
                )
                replacement_results = remover.execute()
                if not replacement_results:
                    self.sprint(f"Failed to replace background in attachment '{attachment.id}'")
                    result = ImageEditManager.Result.partial
                    continue
                self.sprint(f"Image background attachment '{attachment.id}' replaced")
                urls.extend(replacement_results)
            except Exception as e:
                self.sprint(f"Failed to replace background in attachment '{attachment.id}'", e)
                result = ImageEditManager.Result.partial
        if not urls:
            self.sprint("Failed to replace background in all images")
            result = ImageEditManager.Result.failed
        return result, urls

    def execute(self) -> tuple[Result, dict[str, int]]:
        self.sprint(f"Editing images for chat '{self.__chat_id}', operation '{self.__operation.value}'")

        if self.__operation == ImageEditManager.Operation.remove_background:
            result, urls = self.__remove_background()
            for image_url in urls:
                self.sprint(f"Sending edited image to chat '{self.__chat_id}'")
                result_json = self.__bot_api.send_document(self.__chat_id, image_url, thumbnail = image_url)
                if not result_json:
                    raise ValueError("No response from Telegram API")
                self.__store_bot_message(result_json)
                self.sprint("Image edited and sent successfully")
            return result, {"image_backgrounds_removed": len(urls)}

        elif self.__operation == ImageEditManager.Operation.restore_image:
            result, urls = self.__restore_image()
            for image_url in urls:
                self.sprint(f"Sending restored image to chat '{self.__chat_id}': {image_url}")
                result_json = self.__bot_api.send_document(self.__chat_id, image_url, thumbnail = image_url)
                if not result_json:
                    raise ValueError("No response from Telegram API")
                self.__store_bot_message(result_json)
                self.sprint("Image restored and sent successfully")
            return result, {"images_restored": len(urls)}

        elif self.__operation == ImageEditManager.Operation.replace_background:
            result, urls = self.__replace_background()
            for image_url in urls:
                self.sprint(f"Sending images with replaced backgrounds to chat '{self.__chat_id}'")
                result_json = self.__bot_api.send_document(self.__chat_id, image_url, thumbnail = image_url)
                if not result_json:
                    raise ValueError("No response from Telegram API")
                self.__store_bot_message(result_json)
                self.sprint("Backgrounds replaced and images sent successfully")
            return result, {"image_backgrounds_replaced": len(urls)}
        else:
            raise ValueError(f"Unknown operation '{self.__operation.value}'")

    def __store_bot_message(self, api_result: dict):
        self.sprint("Storing message data")
        message = Message(**api_result["result"])
        update = Update(update_id = datetime.now().second, message = message)
        mapping_result = TelegramDomainMapper().map_update(update)
        if not mapping_result:
            raise ValueError("No mapping result from Telegram API")
        # noinspection PyProtectedMember
        resolver = TelegramDataResolver(self.__user_dao._db, self.__bot_api)
        resolution_result = resolver.resolve(mapping_result)
        if not resolution_result.message or not resolution_result.attachments:
            raise ValueError("No resolution result from storing new data")
