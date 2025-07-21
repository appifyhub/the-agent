import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from db.schema.chat_message_attachment import ChatMessageAttachment, ChatMessageAttachmentSave
from di.di import DI
from features.chat.telegram.sdk.telegram_bot_sdk_utils import TelegramBotSDKUtils


class TelegramBotSDKUtilsTest(unittest.TestCase):

    def setUp(self):
        self.mock_di = Mock(spec = DI)
        self.mock_di.telegram_bot_api = Mock()
        self.mock_di.chat_message_attachment_crud = Mock()

        self.attachment_id = "short123"  # Short UUID format
        self.ext_id = "telegram_file_456"  # External Telegram ID
        self.attachment_db = {
            "id": self.attachment_id,
            "ext_id": self.ext_id,
            "chat_id": "chat_123",
            "message_id": "msg_123",
            "size": 1000,
            "last_url": "http://old.url",
            "last_url_until": int(datetime.now().timestamp()),
            "extension": "jpg",
            "mime_type": "image/jpeg",
        }

        self.api_file_info = Mock(
            file_size = 2000,
            file_path = "files/test.png",
        )
        self.mock_di.telegram_bot_api.get_file_info.return_value = self.api_file_info

    def test_refresh_attachments_by_ids_empty_list(self):
        result = TelegramBotSDKUtils.refresh_attachments_by_ids(
            di = self.mock_di,
            attachment_ids = [],
        )
        self.assertEqual(result, [])

    def test_refresh_attachments_by_ids_with_attachments(self):
        attachment_ids = ["short1", "short2"]

        # Mock the get method to return attachment data
        self.mock_di.chat_message_attachment_crud.get.side_effect = [
            {"id": "short1", "ext_id": "ext1", "chat_id": "chat1", "message_id": "msg1"},
            {"id": "short2", "ext_id": "ext2", "chat_id": "chat1", "message_id": "msg2"},
        ]

        with patch.object(TelegramBotSDKUtils, "refresh_attachment") as mock_refresh:
            mock_attachment1 = ChatMessageAttachment(id = "short1", ext_id = "ext1", chat_id = "chat1", message_id = "msg1")
            mock_attachment2 = ChatMessageAttachment(id = "short2", ext_id = "ext2", chat_id = "chat1", message_id = "msg2")
            mock_refresh.side_effect = [mock_attachment1, mock_attachment2]

            result = TelegramBotSDKUtils.refresh_attachments_by_ids(
                di = self.mock_di,
                attachment_ids = attachment_ids,
            )

            self.assertEqual(len(result), 2)
            self.assertEqual(result[0].id, "short1")
            self.assertEqual(result[1].id, "short2")

    def test_refresh_attachment_with_attachment_instance(self):
        attachment = ChatMessageAttachment(
            id = self.attachment_id,
            ext_id = self.ext_id,
            chat_id = "chat_123",
            message_id = "msg_123",
            size = 1000,
        )

        # Mock stale data (URL expired)
        attachment.last_url_until = int(datetime.now().timestamp()) - 3600  # 1 hour ago

        self.mock_di.chat_message_attachment_crud.save.return_value = self.attachment_db

        result = TelegramBotSDKUtils.refresh_attachment(
            di = self.mock_di,
            attachment = attachment,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.id, self.attachment_id)
        self.assertEqual(result.ext_id, self.ext_id)

        # Verify API was called with ext_id
        self.mock_di.telegram_bot_api.get_file_info.assert_called_with(self.ext_id)

    def test_refresh_attachment_with_save_instance(self):
        attachment_save = ChatMessageAttachmentSave(
            id = self.attachment_id,
            ext_id = self.ext_id,
            chat_id = "chat_123",
            message_id = "msg_123",
            size = 500,
        )

        # Create a mock that behaves like a Pydantic model with model_dump()
        class MockAttachmentDB:

            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)

            def model_dump(self):
                return {key: getattr(self, key) for key in self.__dict__}

        mock_db_obj = MockAttachmentDB(self.attachment_db)
        self.mock_di.chat_message_attachment_crud.get.return_value = mock_db_obj
        self.mock_di.chat_message_attachment_crud.get_by_ext_id.return_value = None
        self.mock_di.chat_message_attachment_crud.save.return_value = self.attachment_db

        result = TelegramBotSDKUtils.refresh_attachment(
            di = self.mock_di,
            attachment_save = attachment_save,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.id, self.attachment_id)
        self.assertEqual(result.ext_id, self.ext_id)

    def test_refresh_attachment_fresh_data(self):
        # Test case where data is fresh and doesn't need API call
        attachment = ChatMessageAttachment(
            id = self.attachment_id,
            ext_id = self.ext_id,
            chat_id = "chat_123",
            message_id = "msg_123",
            size = 1000,
            last_url = "http://fresh.url",
            last_url_until = int(datetime.now().timestamp()) + 3600,  # 1 hour in future
        )

        self.mock_di.chat_message_attachment_crud.save.return_value = self.attachment_db

        result = TelegramBotSDKUtils.refresh_attachment(
            di = self.mock_di,
            attachment = attachment,
        )

        self.assertIsNotNone(result)
        # API should NOT be called since data is fresh
        self.mock_di.telegram_bot_api.get_file_info.assert_not_called()

    def test_refresh_attachment_no_ext_id_error(self):
        attachment_save = ChatMessageAttachmentSave(
            id = self.attachment_id,
            ext_id = None,  # Missing ext_id
            chat_id = "chat_123",
            message_id = "msg_123",
        )

        self.mock_di.chat_message_attachment_crud.get.return_value = None
        self.mock_di.chat_message_attachment_crud.get_by_ext_id.return_value = None

        with self.assertRaises(ValueError) as context:
            TelegramBotSDKUtils.refresh_attachment(
                di = self.mock_di,
                attachment_save = attachment_save,
            )

        self.assertIn("No external ID provided", str(context.exception))

    def test_refresh_attachment_no_instance_error(self):
        with self.assertRaises(ValueError) as context:
            TelegramBotSDKUtils.refresh_attachment(
                di = self.mock_di,
            )

        self.assertIn("No attachment instance provided", str(context.exception))

    def test_refresh_attachment_extension_inference(self):
        # Test extension inference from API file path
        attachment = ChatMessageAttachment(
            id = self.attachment_id,
            ext_id = self.ext_id,
            chat_id = "chat_123",
            message_id = "msg_123",
            extension = None,  # No extension initially
            mime_type = None,
        )

        # Mock stale data
        attachment.last_url_until = int(datetime.now().timestamp()) - 3600

        # Mock API response with file path containing extension
        self.api_file_info.file_path = "documents/photo.png"

        updated_attachment_db = dict(self.attachment_db)
        updated_attachment_db["extension"] = "png"
        updated_attachment_db["mime_type"] = "image/png"

        self.mock_di.chat_message_attachment_crud.save.return_value = updated_attachment_db

        result = TelegramBotSDKUtils.refresh_attachment(
            di = self.mock_di,
            attachment = attachment,
        )

        self.assertEqual(result.extension, "png")
        self.assertEqual(result.mime_type, "image/png")

    def test_refresh_attachment_instances(self):
        attachments = [
            ChatMessageAttachment(id = "id1", ext_id = "ext1", chat_id = "chat1", message_id = "msg1"),
            ChatMessageAttachment(id = "id2", ext_id = "ext2", chat_id = "chat1", message_id = "msg2"),
        ]

        with patch.object(TelegramBotSDKUtils, "refresh_attachment") as mock_refresh:
            mock_refresh.side_effect = attachments  # Return the same attachments

            result = TelegramBotSDKUtils.refresh_attachment_instances(
                di = self.mock_di,
                attachments = attachments,
            )

            self.assertEqual(len(result), 2)
            self.assertEqual(mock_refresh.call_count, 2)

    @patch("features.chat.telegram.sdk.telegram_bot_sdk_utils.requests.get")
    @patch.object(TelegramBotSDKUtils, "_TelegramBotSDKUtils__detect_image_format_from_bytes")
    def test_detect_and_set_image_format_jpeg_success(self, mock_detect_format, mock_requests):
        # Mock successful response with JPEG content
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake_jpeg_content"
        mock_requests.return_value = mock_response
        mock_detect_format.return_value = "jpeg"

        # Mock API file info with no file path (triggers image detection)
        api_file = Mock(file_size = 2000, file_path = None)
        self.mock_di.telegram_bot_api.get_file_info.return_value = api_file

        # Mock crud operations to return None (no existing attachment)
        self.mock_di.chat_message_attachment_crud.get.return_value = None
        self.mock_di.chat_message_attachment_crud.get_by_ext_id.return_value = None

        # Mock attachment with no extension/mime_type
        attachment_save = ChatMessageAttachmentSave(
            id = "test123",
            ext_id = "telegram456",
            chat_id = "chat123",
            message_id = "msg123",
            last_url = "http://example.com/image.jpg",
            extension = None,
            mime_type = None,
        )

        # Mock save to return updated attachment
        def mock_save(attachment):
            return attachment.model_dump()

        self.mock_di.chat_message_attachment_crud.save.side_effect = mock_save

        result = TelegramBotSDKUtils.refresh_attachment(self.mock_di, attachment_save = attachment_save)

        self.assertEqual(result.extension, "jpeg")
        self.assertEqual(result.mime_type, "image/jpeg")
        mock_requests.assert_called_once_with("http://example.com/image.jpg", timeout = 10)
        mock_detect_format.assert_called_once_with(b"fake_jpeg_content")

    @patch("features.chat.telegram.sdk.telegram_bot_sdk_utils.requests.get")
    @patch.object(TelegramBotSDKUtils, "_TelegramBotSDKUtils__detect_image_format_from_bytes")
    def test_refresh_attachment_detects_image_format_when_missing(self, mock_detect_format, mock_requests):
        """Test that refresh_attachment detects image format when extension and mime_type are None"""
        # Mock successful response with JPEG content
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake_jpeg_content"
        mock_requests.return_value = mock_response
        mock_detect_format.return_value = "png"  # Test PNG detection

        # Mock API file info with no file path (triggers image detection)
        api_file = Mock(file_size = 2000, file_path = None)
        self.mock_di.telegram_bot_api.get_file_info.return_value = api_file

        # Mock crud operations to return None (no existing attachment)
        self.mock_di.chat_message_attachment_crud.get.return_value = None
        self.mock_di.chat_message_attachment_crud.get_by_ext_id.return_value = None

        # Mock attachment with no extension/mime_type (typical Telegram photo)
        attachment_save = ChatMessageAttachmentSave(
            id = "test123",
            ext_id = "telegram456",
            chat_id = "chat123",
            message_id = "msg123",
            last_url = "http://example.com/image.jpg",
            extension = None,
            mime_type = None,
        )

        # Mock save to return updated attachment
        def mock_save(attachment):
            return attachment.model_dump()

        self.mock_di.chat_message_attachment_crud.save.side_effect = mock_save

        result = TelegramBotSDKUtils.refresh_attachment(self.mock_di, attachment_save = attachment_save)

        # Verify image format was detected and set
        self.assertEqual(result.extension, "png")
        self.assertEqual(result.mime_type, "image/png")
        mock_requests.assert_called_once_with("http://example.com/image.jpg", timeout = 10)
        mock_detect_format.assert_called_once_with(b"fake_jpeg_content")

    @patch("features.chat.telegram.sdk.telegram_bot_sdk_utils.requests.get")
    def test_refresh_attachment_handles_image_detection_failure(self, mock_requests):
        """Test that refresh_attachment handles image detection failures gracefully"""
        # Mock request failure
        mock_requests.side_effect = Exception("Network error")

        # Mock API file info with no file path (triggers image detection)
        api_file = Mock(file_size = 2000, file_path = None)
        self.mock_di.telegram_bot_api.get_file_info.return_value = api_file

        # Mock crud operations to return None (no existing attachment)
        self.mock_di.chat_message_attachment_crud.get.return_value = None
        self.mock_di.chat_message_attachment_crud.get_by_ext_id.return_value = None

        attachment_save = ChatMessageAttachmentSave(
            id = "test123",
            ext_id = "telegram456",
            chat_id = "chat123",
            message_id = "msg123",
            last_url = "http://example.com/image.jpg",
            extension = None,
            mime_type = None,
        )

        # Mock save to return updated attachment
        def mock_save(attachment):
            return attachment.model_dump()

        self.mock_di.chat_message_attachment_crud.save.side_effect = mock_save

        # Should not raise exception, just continue with None values
        result = TelegramBotSDKUtils.refresh_attachment(self.mock_di, attachment_save = attachment_save)

        # Values should remain None due to detection failure
        self.assertIsNone(result.extension)
        self.assertIsNone(result.mime_type)
