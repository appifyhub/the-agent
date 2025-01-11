import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from db.crud.chat_message_attachment import ChatMessageAttachmentCRUD
from db.schema.chat_message_attachment import ChatMessageAttachmentSave, ChatMessageAttachment
from features.chat.telegram.sdk.telegram_bot_api import TelegramBotAPI
from features.chat.telegram.sdk.telegram_bot_sdk_utils import TelegramBotSDKUtils


class TelegramBotSDKUtilsTest(unittest.TestCase):

    def setUp(self):
        self.mock_bot_api = Mock(spec = TelegramBotAPI)
        self.mock_attachment_dao = Mock(spec = ChatMessageAttachmentCRUD)

        self.attachment_id = "test_file_123"
        self.attachment_db = {
            "id": self.attachment_id,
            "chat_id": "chat_123",
            "message_id": "msg_123",
            "size": 1000,
            "last_url": "http://old.url",
            "last_url_until": int(datetime.now().timestamp()),
            "extension": "jpg",
            "mime_type": "image/jpeg"
        }

        self.api_file_info = Mock(
            file_size = 2000,
            file_path = "files/test.png"
        )
        self.mock_bot_api.get_file_info.return_value = self.api_file_info

    def test_refresh_attachments_empty_list(self):
        result = TelegramBotSDKUtils.refresh_attachments(
            sources = [],
            bot_api = self.mock_bot_api,
            chat_message_attachment_dao = self.mock_attachment_dao
        )
        self.assertEqual(result, [])

    @patch.object(TelegramBotSDKUtils, "refresh_attachment")
    def test_refresh_attachments_with_sources(self, mock_refresh):
        sources = ["id1", "id2"]
        mock_refresh.side_effect = [
            ChatMessageAttachment(id = "id1", chat_id = "chat1", message_id = "msg1"),
            ChatMessageAttachment(id = "id2", chat_id = "chat1", message_id = "msg2")
        ]

        result = TelegramBotSDKUtils.refresh_attachments(
            sources = sources,
            bot_api = self.mock_bot_api,
            chat_message_attachment_dao = self.mock_attachment_dao
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(mock_refresh.call_count, 2)

    def test_refresh_attachment_string_id_not_found(self):
        self.mock_attachment_dao.get.return_value = None

        with self.assertRaises(ValueError) as context:
            TelegramBotSDKUtils.refresh_attachment(
                source = self.attachment_id,
                bot_api = self.mock_bot_api,
                chat_message_attachment_dao = self.mock_attachment_dao
            )
        self.assertTrue("not found in DB" in str(context.exception))

    def test_refresh_attachment_fresh_data(self):
        attachment = ChatMessageAttachmentSave(
            id = self.attachment_id,
            chat_id = "chat_123",
            message_id = "msg_123",
            last_url = "http://fresh.url",
            last_url_until = int((datetime.now().timestamp()) + 3600)
        )

        self.mock_attachment_dao.save.return_value = attachment.model_dump()

        result = TelegramBotSDKUtils.refresh_attachment(
            source = attachment,
            bot_api = self.mock_bot_api,
            chat_message_attachment_dao = self.mock_attachment_dao
        )

        self.assertEqual(result.id, attachment.id)
        self.mock_bot_api.get_file_info.assert_not_called()

    @patch.object(TelegramBotSDKUtils, "_TelegramBotSDKUtils__nearest_hour_epoch")
    def test_refresh_attachment_stale_data(self, mock_nearest_hour):
        mock_nearest_hour.return_value = int(datetime.now().timestamp()) + 3600

        stale_attachment = ChatMessageAttachmentSave(
            id = self.attachment_id,
            chat_id = "chat_123",
            message_id = "msg_123",
            last_url = "http://stale.url",
            last_url_until = int(datetime.now().timestamp()) - 3600
        )

        self.mock_attachment_dao.get.return_value = stale_attachment.model_dump()
        self.mock_attachment_dao.save.return_value = {
            **stale_attachment.model_dump(),
            "last_url": "http://new.url",
            "size": 2000
        }

        result = TelegramBotSDKUtils.refresh_attachment(
            source = stale_attachment,
            bot_api = self.mock_bot_api,
            chat_message_attachment_dao = self.mock_attachment_dao
        )

        self.mock_bot_api.get_file_info.assert_called_once_with(self.attachment_id)
        self.assertNotEqual(result.last_url, stale_attachment.last_url)
        self.assertEqual(result.size, 2000)

    def test_nearest_hour_epoch(self):
        mock_now = datetime(2024, 1, 1, 10, 30, 45)
        expected_next_hour = datetime(2024, 1, 1, 11, 0, 0)

        with patch(f"{TelegramBotSDKUtils.__module__}.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.datetime = datetime

            # noinspection PyUnresolvedReferences
            result = TelegramBotSDKUtils._TelegramBotSDKUtils__nearest_hour_epoch()

            self.assertEqual(result, int(expected_next_hour.timestamp()))
