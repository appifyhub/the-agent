import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

from pydantic import SecretStr

from db.model.chat_config import ChatConfigDB
from db.model.chat_message_attachment import ChatMessageAttachmentDB
from db.model.user import UserDB
from db.schema.chat_message_attachment import ChatMessageAttachment
from db.schema.user import User
from features.chat.chat_image_edit_service import ChatImageEditService


class ChatImageEditServiceTest(unittest.TestCase):

    def setUp(self):
        self.attachment_ids = ["attachment1", "attachment2"]
        self.operation_guidance = None
        self.mock_di = MagicMock()
        self.mock_platform_sdk = MagicMock()
        self.mock_di.platform_bot_sdk = MagicMock(return_value = self.mock_platform_sdk)
        self.mock_di.telegram_bot_api = MagicMock()
        self.mock_di.user_dao = MagicMock()
        self.mock_di.chat_message_attachment_crud = MagicMock()
        self.mock_di.access_token_resolver = MagicMock()
        mock_chat = MagicMock()
        mock_chat.external_id = "test_chat_id"
        mock_chat.chat_type = ChatConfigDB.ChatType.telegram
        mock_chat.media_mode = ChatConfigDB.MediaMode.all  # Default to 'all' mode to match old behavior
        self.mock_di.require_invoker_chat = MagicMock(return_value = mock_chat)
        self.mock_di.require_invoker_chat_type = MagicMock(return_value = ChatConfigDB.ChatType.telegram)
        self.mock_di.tool_choice_resolver = MagicMock()
        self.mock_di.image_editor = MagicMock()

        self.user = User(
            id = UUID(hex = "123e4567-e89b-12d3-a456-426614174000"),
            full_name = "Test User",
            telegram_username = "test_username",
            telegram_chat_id = "test_chat_id",
            telegram_user_id = 1,
            open_ai_key = SecretStr("test_api_key"),
            replicate_key = SecretStr("test_replicate_key"),
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.mock_di.user_dao.get.return_value = self.user

        # Create a mock ChatMessageAttachmentDB instance
        self.mock_attachment_db = ChatMessageAttachmentDB(
            id = "attachment1",
            external_id = "telegram_file_1",
            chat_id = UUID(int = 1),
            message_id = "message1",
            size = 1024,
            last_url = "http://test.com/image.png",
            last_url_until = int(datetime.now().timestamp()) + 3600,
            extension = "png",
            mime_type = "image/png",
        )
        self.mock_di.chat_message_attachment_crud.get.return_value = self.mock_attachment_db
        self.attachment = ChatMessageAttachment.model_validate(self.mock_attachment_db)

        # Mock the SDK refresh_attachments_by_ids method
        self.patcher = patch.object(self.mock_platform_sdk, "refresh_attachments_by_ids")
        self.mock_refresh = self.patcher.start()
        self.mock_refresh.return_value = [ChatMessageAttachment.model_validate(self.mock_attachment_db)]

    def tearDown(self):
        self.patcher.stop()

    def test_init_success(self):
        with patch.object(self.mock_platform_sdk, "refresh_attachments_by_ids", return_value = [self.attachment]):
            service = ChatImageEditService(
                attachment_ids = self.attachment_ids,
                operation_guidance = self.operation_guidance,
                aspect_ratio = None,
                output_size = None,
                di = self.mock_di,
            )
            self.assertIsInstance(service, ChatImageEditService)

    def test_execute_edit_image_partial(self):
        self.mock_platform_sdk.refresh_attachments_by_ids.return_value = [self.attachment, self.attachment]
        mock_editor_instance1 = MagicMock()
        mock_editor_instance1.execute.return_value = "http://test.com/edited_image.png"
        mock_editor_instance1.error = None
        mock_editor_instance2 = MagicMock()
        mock_editor_instance2.execute.return_value = None
        mock_editor_instance2.error = "Processing failed"
        self.mock_di.image_editor.side_effect = [mock_editor_instance1, mock_editor_instance2]
        self.mock_platform_sdk.send_document.return_value = {"result": {"message_id": 123}}
        self.mock_platform_sdk.send_photo.return_value = {"result": {"message_id": 124}}

        service = ChatImageEditService(
            attachment_ids = self.attachment_ids,
            operation_guidance = self.operation_guidance,
            aspect_ratio = None,
            output_size = None,
            di = self.mock_di,
        )
        result, details = service.execute()

        self.assertEqual(result, ChatImageEditService.Result.partial)
        expected_details = [
            {"url": "http://test.com/edited_image.png", "error": None, "status": "delivered"},
            {"url": None, "error": "Error editing image from attachment 'attachment1': Processing failed"},
        ]
        self.assertEqual(details, expected_details)
        self.assertEqual(self.mock_di.image_editor.call_count, 2)
        self.mock_platform_sdk.smart_send_photo.assert_called_once_with(
            media_mode = ChatConfigDB.MediaMode.all,
            chat_id = "test_chat_id",
            photo_url = "http://test.com/edited_image.png",
            caption = "📸",
            thumbnail = "http://test.com/edited_image.png",
        )

    def test_execute_edit_image_failed(self):
        self.mock_platform_sdk.refresh_attachments_by_ids.return_value = [self.attachment]
        mock_editor_instance = MagicMock()
        mock_editor_instance.execute.return_value = None
        mock_editor_instance.error = "Image editing failed"
        self.mock_di.image_editor.return_value = mock_editor_instance

        service = ChatImageEditService(
            attachment_ids = self.attachment_ids,
            operation_guidance = self.operation_guidance,
            aspect_ratio = None,
            output_size = None,
            di = self.mock_di,
        )
        result, details = service.execute()

        self.assertEqual(result, ChatImageEditService.Result.failed)
        expected_details = [
            {"url": None, "error": "Error editing image from attachment 'attachment1': Image editing failed"},
        ]
        self.assertEqual(details, expected_details)
        mock_editor_instance.execute.assert_called_once()
        self.mock_platform_sdk.send_document.assert_not_called()

    def test_execute_edit_image_exception(self):
        self.mock_platform_sdk.refresh_attachments_by_ids.return_value = [self.attachment]
        mock_editor_instance = MagicMock()
        mock_editor_instance.execute.side_effect = Exception("Test exception")
        mock_editor_instance.error = None
        self.mock_di.image_editor.return_value = mock_editor_instance

        service = ChatImageEditService(
            attachment_ids = self.attachment_ids,
            operation_guidance = self.operation_guidance,
            aspect_ratio = None,
            output_size = None,
            di = self.mock_di,
        )
        result, details = service.execute()

        self.assertEqual(result, ChatImageEditService.Result.failed)
        expected_details = [
            {
                "url": None,
                "error": (
                    "Failed to edit image from attachment 'attachment1'\n"
                    " ├─ ! Exception (see below)\n"
                    " ├─ Exception: Test exception"
                ),
            },
        ]
        self.assertEqual(details, expected_details)
        mock_editor_instance.execute.assert_called_once()
        self.mock_platform_sdk.send_document.assert_not_called()

    def test_execute_edit_image_success(self):
        self.mock_platform_sdk.refresh_attachments_by_ids.return_value = [self.attachment]
        mock_editor_instance = MagicMock()
        mock_editor_instance.execute.return_value = "http://test.com/edited_image.png"
        mock_editor_instance.error = None
        self.mock_di.image_editor.return_value = mock_editor_instance
        self.mock_platform_sdk.send_document.return_value = {"result": {"message_id": 123}}
        self.mock_platform_sdk.send_photo.return_value = {"result": {"message_id": 124}}

        service = ChatImageEditService(
            attachment_ids = self.attachment_ids,
            operation_guidance = self.operation_guidance,
            aspect_ratio = None,
            output_size = None,
            di = self.mock_di,
        )
        result, details = service.execute()

        self.assertEqual(result, ChatImageEditService.Result.success)
        expected_details = [{"url": "http://test.com/edited_image.png", "error": None, "status": "delivered"}]
        self.assertEqual(details, expected_details)
        mock_editor_instance.execute.assert_called_once()
        self.mock_platform_sdk.smart_send_photo.assert_called_once_with(
            media_mode = ChatConfigDB.MediaMode.all,
            chat_id = "test_chat_id",
            photo_url = "http://test.com/edited_image.png",
            caption = "📸",
            thumbnail = "http://test.com/edited_image.png",
        )
