import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

from db.model.chat_message_attachment import ChatMessageAttachmentDB
from db.model.user import UserDB
from db.schema.chat_message_attachment import ChatMessageAttachment
from db.schema.user import User
from features.chat.chat_imaging_service import ChatImagingService
from features.chat.telegram.sdk.telegram_bot_sdk_utils import TelegramBotSDKUtils
from features.images.image_contents_restorer import ImageContentsRestorer


class ImageGeneratorTest(unittest.TestCase):

    def setUp(self):
        self.attachment_ids = ["attachment1", "attachment2"]
        self.operation_name = "remove-background"
        self.operation_guidance = None
        self.mock_di = MagicMock()
        self.mock_di.telegram_bot_sdk = MagicMock()
        self.mock_di.telegram_bot_api = MagicMock()
        self.mock_di.user_dao = MagicMock()
        self.mock_di.chat_message_attachment_crud = MagicMock()
        self.mock_di.access_token_resolver = MagicMock()
        self.mock_di.invoker_chat = MagicMock()
        self.mock_di.invoker_chat.chat_id = "test_chat_id"
        self.mock_di.tool_choice_resolver = MagicMock()
        self.mock_di.image_background_remover = MagicMock()
        self.mock_di.image_contents_restorer = MagicMock()
        self.mock_di.image_editor = MagicMock()

        self.user = User(
            id = UUID(hex = "123e4567-e89b-12d3-a456-426614174000"),
            full_name = "Test User",
            telegram_username = "test_username",
            telegram_chat_id = "test_chat_id",
            telegram_user_id = 1,
            open_ai_key = "test_api_key",
            replicate_key = "test_replicate_key",
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.mock_di.user_dao.get.return_value = self.user

        # Create a mock ChatMessageAttachmentDB instance
        self.mock_attachment_db = ChatMessageAttachmentDB(
            id = "attachment1",
            ext_id = "telegram_file_1",
            chat_id = "test_chat_id",
            message_id = "message1",
            size = 1024,
            last_url = "http://test.com/image.png",
            last_url_until = int(datetime.now().timestamp()) + 3600,
            extension = "png",
            mime_type = "image/png",
        )
        self.mock_di.chat_message_attachment_crud.get.return_value = self.mock_attachment_db
        self.attachment = ChatMessageAttachment.model_validate(self.mock_attachment_db)

        # Mock the refresh_attachments_by_ids method
        self.patcher = patch.object(TelegramBotSDKUtils, "refresh_attachments_by_ids")
        self.mock_refresh = self.patcher.start()
        self.mock_refresh.return_value = [ChatMessageAttachment.model_validate(self.mock_attachment_db)]

    def tearDown(self):
        self.patcher.stop()

    def test_init_success(self):
        with patch.object(TelegramBotSDKUtils, "refresh_attachments_by_ids", return_value = [self.attachment]):
            service = ChatImagingService(
                attachment_ids = self.attachment_ids,
                operation_name = self.operation_name,
                operation_guidance = self.operation_guidance,
                di = self.mock_di,
            )
            self.assertIsInstance(service, ChatImagingService)

    def test_init_invalid_operation(self):
        with self.assertRaises(ValueError):
            ChatImagingService(
                attachment_ids = self.attachment_ids,
                operation_name = "invalid-operation",
                operation_guidance = self.operation_guidance,
                di = self.mock_di,
            )

    @patch.object(TelegramBotSDKUtils, "refresh_attachments_by_ids")
    def test_execute_remove_background_partial(self, mock_refresh):
        mock_refresh.return_value = [self.attachment, self.attachment]
        mock_remover_instance1 = MagicMock()
        mock_remover_instance1.execute.return_value = "http://test.com/edited_image.png"
        mock_remover_instance1.error = None
        mock_remover_instance2 = MagicMock()
        mock_remover_instance2.execute.return_value = None
        mock_remover_instance2.error = "Processing failed"
        self.mock_di.image_background_remover.side_effect = [mock_remover_instance1, mock_remover_instance2]
        self.mock_di.telegram_bot_sdk.send_document.return_value = {"result": {"message_id": 123}}
        self.mock_di.telegram_bot_sdk.send_photo.return_value = {"result": {"message_id": 124}}

        service = ChatImagingService(
            attachment_ids = self.attachment_ids,
            operation_name = "remove-background",
            operation_guidance = self.operation_guidance,
            di = self.mock_di,
        )
        result, details = service.execute()

        self.assertEqual(result, ChatImagingService.Result.partial)
        expected_details = [
            {"url": "http://test.com/edited_image.png", "error": None, "status": "delivered"},
            {"url": None, "error": "Processing failed"},
        ]
        self.assertEqual(details, expected_details)
        self.assertEqual(self.mock_di.image_background_remover.call_count, 2)
        self.mock_di.telegram_bot_sdk.send_document.assert_called_once_with(
            self.mock_di.invoker_chat.chat_id,
            "http://test.com/edited_image.png",
            thumbnail = "http://test.com/edited_image.png",
        )

    @patch.object(TelegramBotSDKUtils, "refresh_attachments_by_ids")
    def test_execute_remove_background_failed(self, mock_refresh):
        mock_refresh.return_value = [self.attachment]
        mock_remover_instance = MagicMock()
        mock_remover_instance.execute.return_value = None
        mock_remover_instance.error = "Background removal failed"
        self.mock_di.image_background_remover.return_value = mock_remover_instance

        service = ChatImagingService(
            attachment_ids = self.attachment_ids,
            operation_name = "remove-background",
            operation_guidance = self.operation_guidance,
            di = self.mock_di,
        )
        result, details = service.execute()

        self.assertEqual(result, ChatImagingService.Result.failed)
        expected_details = [{"url": None, "error": "Background removal failed"}]
        self.assertEqual(details, expected_details)
        mock_remover_instance.execute.assert_called_once()
        self.mock_di.telegram_bot_sdk.send_document.assert_not_called()

    @patch.object(TelegramBotSDKUtils, "refresh_attachments_by_ids")
    def test_execute_remove_background_exception(self, mock_refresh):
        mock_refresh.return_value = [self.attachment]
        mock_remover_instance = MagicMock()
        mock_remover_instance.execute.side_effect = Exception("Test exception")
        mock_remover_instance.error = None
        self.mock_di.image_background_remover.return_value = mock_remover_instance

        service = ChatImagingService(
            attachment_ids = self.attachment_ids,
            operation_name = "remove-background",
            operation_guidance = self.operation_guidance,
            di = self.mock_di,
        )
        result, details = service.execute()

        self.assertEqual(result, ChatImagingService.Result.failed)
        expected_details = [{"url": None, "error": "Test exception"}]
        self.assertEqual(details, expected_details)
        mock_remover_instance.execute.assert_called_once()
        self.mock_di.telegram_bot_sdk.send_document.assert_not_called()

    @patch.object(TelegramBotSDKUtils, "refresh_attachments_by_ids")
    def test_execute_unknown_operation(self, mock_refresh):
        mock_refresh.return_value = [self.attachment]
        # Patch Operation.resolve to return a mock operation with value 'unknown-operation'
        with patch.object(ChatImagingService.Operation, "resolve", return_value = MagicMock(value = "unknown-operation")):
            service = ChatImagingService(
                attachment_ids = self.attachment_ids,
                operation_name = "remove-background",
                operation_guidance = self.operation_guidance,
                di = self.mock_di,
            )
            with self.assertRaises(ValueError):
                service.execute()

    @patch.object(TelegramBotSDKUtils, "refresh_attachments_by_ids")
    def test_execute_remove_background_success(self, mock_refresh):
        mock_refresh.return_value = [self.attachment]
        mock_remover_instance = MagicMock()
        mock_remover_instance.execute.return_value = "http://test.com/edited_image.png"
        mock_remover_instance.error = None
        self.mock_di.image_background_remover.return_value = mock_remover_instance
        self.mock_di.telegram_bot_sdk.send_document.return_value = {"result": {"message_id": 123}}
        self.mock_di.telegram_bot_sdk.send_photo.return_value = {"result": {"message_id": 124}}

        service = ChatImagingService(
            attachment_ids = self.attachment_ids,
            operation_name = "remove-background",
            operation_guidance = self.operation_guidance,
            di = self.mock_di,
        )
        result, details = service.execute()

        self.assertEqual(result, ChatImagingService.Result.success)
        expected_details = [{"url": "http://test.com/edited_image.png", "error": None, "status": "delivered"}]
        self.assertEqual(details, expected_details)
        mock_remover_instance.execute.assert_called_once()
        self.mock_di.telegram_bot_sdk.send_document.assert_called_once_with(
            self.mock_di.invoker_chat.chat_id,
            "http://test.com/edited_image.png",
            thumbnail = "http://test.com/edited_image.png",
        )

    @patch.object(TelegramBotSDKUtils, "refresh_attachments_by_ids")
    def test_execute_restore_image_success(self, mock_refresh):
        mock_refresh.return_value = [self.attachment]
        mock_restorer_instance = MagicMock()
        mock_restorer_instance.execute.return_value = ImageContentsRestorer.Result(
            restored_url = "http://test.com/restored_image.png",
            inpainted_url = "http://test.com/inpainted_image.png",
            error = None,
        )
        self.mock_di.image_contents_restorer.return_value = mock_restorer_instance
        self.mock_di.telegram_bot_sdk.send_document.return_value = {"result": {"message_id": 123}}
        self.mock_di.telegram_bot_sdk.send_photo.return_value = {"result": {"message_id": 124}}

        service = ChatImagingService(
            attachment_ids = self.attachment_ids,
            operation_name = "restore-image",
            operation_guidance = self.operation_guidance,
            di = self.mock_di,
        )
        result, details = service.execute()

        self.assertEqual(result, ChatImagingService.Result.success)
        expected_details = [{"url": "http://test.com/inpainted_image.png", "error": None, "status": "delivered"}]
        self.assertEqual(details, expected_details)
        mock_restorer_instance.execute.assert_called_once()
        self.mock_di.telegram_bot_sdk.send_document.assert_called_once()
