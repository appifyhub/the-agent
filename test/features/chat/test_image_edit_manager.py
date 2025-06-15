import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

from db.crud.chat_message_attachment import ChatMessageAttachmentCRUD
from db.crud.user import UserCRUD
from db.model.chat_message_attachment import ChatMessageAttachmentDB
from db.model.user import UserDB
from db.schema.chat_message_attachment import ChatMessageAttachment
from db.schema.user import User
from features.chat.image_edit_manager import ImageEditManager
from features.chat.telegram.sdk.telegram_bot_api import TelegramBotAPI
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.chat.telegram.sdk.telegram_bot_sdk_utils import TelegramBotSDKUtils
from features.images.image_background_remover import ImageBackgroundRemover
from features.images.image_contents_restorer import ImageContentsRestorer


class ImageEditManagerTest(unittest.TestCase):

    def setUp(self):
        self.chat_id = "test_chat_id"
        self.attachment_ids = ["attachment1", "attachment2"]
        self.invoker_user_id_hex = "123e4567-e89b-12d3-a456-426614174000"
        self.operation_name = "remove-background"
        self.mock_bot_sdk = MagicMock(spec = TelegramBotSDK)
        self.mock_bot_sdk.api = MagicMock(spec = TelegramBotAPI)
        self.mock_user_dao = MagicMock(spec = UserCRUD)
        self.mock_chat_message_attachment_dao = MagicMock(spec = ChatMessageAttachmentCRUD)

        self.user = User(
            id = UUID(hex = self.invoker_user_id_hex),
            full_name = "Test User",
            telegram_username = "test_username",
            telegram_chat_id = "test_chat_id",
            telegram_user_id = 1,
            open_ai_key = "test_api_key",
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.mock_user_dao.get.return_value = self.user

        # Create a mock ChatMessageAttachmentDB instance
        self.mock_attachment_db = ChatMessageAttachmentDB(
            id = "attachment1",
            chat_id = self.chat_id,
            message_id = "message1",
            size = 1024,
            last_url = "http://test.com/image.png",
            last_url_until = int(datetime.now().timestamp()) + 3600,
            extension = "png",
            mime_type = "image/png",
        )
        self.mock_chat_message_attachment_dao.get.return_value = self.mock_attachment_db
        self.attachment = ChatMessageAttachment.model_validate(self.mock_attachment_db)

        # Mock the refresh_attachments method
        self.patcher = patch.object(TelegramBotSDKUtils, "refresh_attachments")
        self.mock_refresh = self.patcher.start()
        self.mock_refresh.return_value = [ChatMessageAttachment.model_validate(self.mock_attachment_db)]

    def tearDown(self):
        self.patcher.stop()

    def test_init_success(self):
        with patch.object(TelegramBotSDKUtils, "refresh_attachments", return_value = [self.attachment]):
            manager = ImageEditManager(
                self.chat_id,
                self.attachment_ids,
                self.invoker_user_id_hex,
                self.operation_name,
                self.mock_bot_sdk,
                self.mock_user_dao,
                self.mock_chat_message_attachment_dao,
            )
            self.assertIsInstance(manager, ImageEditManager)

    def test_init_user_not_found(self):
        self.mock_user_dao.get.return_value = None
        with self.assertRaises(ValueError):
            ImageEditManager(
                self.chat_id,
                self.attachment_ids,
                self.invoker_user_id_hex,
                self.operation_name,
                self.mock_bot_sdk,
                self.mock_user_dao,
                self.mock_chat_message_attachment_dao,
            )

    def test_init_invalid_operation(self):
        with self.assertRaises(ValueError):
            ImageEditManager(
                self.chat_id,
                self.attachment_ids,
                self.invoker_user_id_hex,
                "invalid-operation",
                self.mock_bot_sdk,
                self.mock_user_dao,
                self.mock_chat_message_attachment_dao,
            )

    @patch.object(TelegramBotSDKUtils, "refresh_attachments")
    @patch.object(ImageBackgroundRemover, "execute")
    def test_execute_remove_background_partial(self, mock_remove_bg, mock_refresh):
        mock_refresh.return_value = [self.attachment, self.attachment]
        mock_remove_bg.side_effect = ["http://test.com/edited_image.png", None]
        self.mock_bot_sdk.send_document.return_value = {"result": {"message_id": 123}}

        manager = ImageEditManager(
            self.chat_id,
            self.attachment_ids,
            self.invoker_user_id_hex,
            "remove-background",
            self.mock_bot_sdk,
            self.mock_user_dao,
            self.mock_chat_message_attachment_dao,
        )
        result, stats = manager.execute()

        self.assertEqual(result, ImageEditManager.Result.partial)
        self.assertEqual(stats, {"image_backgrounds_removed": 1})
        self.assertEqual(mock_remove_bg.call_count, 2)
        self.mock_bot_sdk.send_document.assert_called_once_with(
            self.chat_id,
            "http://test.com/edited_image.png",
            thumbnail = "http://test.com/edited_image.png",
        )

    @patch.object(TelegramBotSDKUtils, "refresh_attachments")
    @patch.object(ImageBackgroundRemover, "execute")
    def test_execute_remove_background_failed(self, mock_remove_bg, mock_refresh):
        mock_refresh.return_value = [self.attachment]
        mock_remove_bg.return_value = None

        manager = ImageEditManager(
            self.chat_id,
            self.attachment_ids,
            self.invoker_user_id_hex,
            "remove-background",
            self.mock_bot_sdk,
            self.mock_user_dao,
            self.mock_chat_message_attachment_dao,
        )
        result, stats = manager.execute()

        self.assertEqual(result, ImageEditManager.Result.failed)
        self.assertEqual(stats, {"image_backgrounds_removed": 0})
        mock_remove_bg.assert_called_once()
        self.mock_bot_sdk.send_document.assert_not_called()

    @patch.object(TelegramBotSDKUtils, "refresh_attachments")
    @patch.object(ImageBackgroundRemover, "execute")
    def test_execute_remove_background_exception(self, mock_remove_bg, mock_refresh):
        mock_refresh.return_value = [self.attachment]
        mock_remove_bg.side_effect = Exception("Test exception")

        manager = ImageEditManager(
            self.chat_id,
            self.attachment_ids,
            self.invoker_user_id_hex,
            "remove-background",
            self.mock_bot_sdk,
            self.mock_user_dao,
            self.mock_chat_message_attachment_dao,
        )
        result, stats = manager.execute()

        self.assertEqual(result, ImageEditManager.Result.failed)
        self.assertEqual(stats, {"image_backgrounds_removed": 0})
        mock_remove_bg.assert_called_once()
        self.mock_bot_sdk.send_document.assert_not_called()

    @patch.object(TelegramBotSDKUtils, "refresh_attachments")
    def test_execute_unknown_operation(self, mock_refresh):
        mock_refresh.return_value = [self.attachment]

        manager = ImageEditManager(
            self.chat_id,
            self.attachment_ids,
            self.invoker_user_id_hex,
            "remove-background",  # This is set to a valid operation to pass initialization
            self.mock_bot_sdk,
            self.mock_user_dao,
            self.mock_chat_message_attachment_dao,
        )
        # We're forcibly changing the operation to an invalid one to test the execution
        manager._ImageEditManager__operation = MagicMock()
        manager._ImageEditManager__operation.value = "unknown-operation"

        with self.assertRaises(ValueError):
            manager.execute()

    @patch.object(TelegramBotSDKUtils, "refresh_attachments")
    @patch.object(ImageBackgroundRemover, "execute")
    def test_execute_remove_background_success(self, mock_remove_bg, mock_refresh):
        mock_refresh.return_value = [self.attachment]
        mock_remove_bg.return_value = "http://test.com/edited_image.png"
        self.mock_bot_sdk.send_document.return_value = {"result": {"message_id": 123}}

        manager = ImageEditManager(
            self.chat_id,
            self.attachment_ids,
            self.invoker_user_id_hex,
            "remove-background",
            self.mock_bot_sdk,
            self.mock_user_dao,
            self.mock_chat_message_attachment_dao,
        )
        result, stats = manager.execute()

        self.assertEqual(result, ImageEditManager.Result.success)
        self.assertEqual(stats, {"image_backgrounds_removed": 1})
        mock_remove_bg.assert_called_once()
        self.mock_bot_sdk.send_document.assert_called_once_with(
            self.chat_id,
            "http://test.com/edited_image.png",
            thumbnail = "http://test.com/edited_image.png",
        )

    @patch.object(TelegramBotSDKUtils, "refresh_attachments")
    @patch.object(ImageContentsRestorer, "execute")
    def test_execute_restore_image_success(self, mock_restore, mock_refresh):
        mock_refresh.return_value = [self.attachment]
        mock_restore.return_value = ImageContentsRestorer.Result(
            restored_url = "http://test.com/restored_image.png",
            inpainted_url = "http://test.com/inpainted_image.png",
        )
        self.mock_bot_sdk.send_document.return_value = {"result": {"message_id": 123}}

        manager = ImageEditManager(
            self.chat_id,
            self.attachment_ids,
            self.invoker_user_id_hex,
            "restore-image",
            self.mock_bot_sdk,
            self.mock_user_dao,
            self.mock_chat_message_attachment_dao,
        )
        result, stats = manager.execute()

        self.assertEqual(result, ImageEditManager.Result.success)
        self.assertEqual(stats, {"images_restored": 2})
        mock_restore.assert_called_once()
        self.assertEqual(self.mock_bot_sdk.send_document.call_count, 2)
