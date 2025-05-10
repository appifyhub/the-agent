import unittest
from unittest.mock import Mock

from db.schema.chat_config import ChatConfig
from features.chat.chat_config_manager import ChatConfigManager


class ChatConfigManagerTest(unittest.TestCase):
    chat_config: ChatConfig
    mock_chat_config_dao: Mock
    manager: ChatConfigManager

    def setUp(self):
        self.chat_config = ChatConfig(
            chat_id = "test_chat_id",
            language_iso_code = "English",
            language_name = "en",
            reply_chance_percent = 100,
        )
        self.mock_chat_config_dao = Mock()
        self.manager = ChatConfigManager(self.mock_chat_config_dao)

    def test_change_chat_language_success(self):
        self.mock_chat_config_dao.get.return_value = self.chat_config
        self.mock_chat_config_dao.save.return_value = self.chat_config

        result, message = self.manager.change_chat_language("test_chat_id", "Spanish", "es")

        self.assertEqual(result, ChatConfigManager.Result.success)
        self.assertIn("Chat language changed to Spanish ('ES')", message)
        self.mock_chat_config_dao.get.assert_called_once_with("test_chat_id")
        self.mock_chat_config_dao.save.assert_called()

    def test_change_chat_language_failure_chat_not_found(self):
        self.mock_chat_config_dao.get.return_value = None

        result, message = self.manager.change_chat_language("test_chat_id", "Spanish", "es")

        self.assertEqual(result, ChatConfigManager.Result.failure)
        self.assertIn("Chat 'test_chat_id' not found", message)

    def test_change_chat_reply_chance_success(self):
        self.mock_chat_config_dao.get.return_value = self.chat_config
        self.mock_chat_config_dao.save.return_value = self.chat_config

        result, message = self.manager.change_chat_reply_chance("test_chat_id", 50)

        self.assertEqual(result, ChatConfigManager.Result.success)
        self.assertIn("Reply chance is now set to 50%", message)
        self.mock_chat_config_dao.get.assert_called_once_with("test_chat_id")
        self.mock_chat_config_dao.save.assert_called()

    def test_change_chat_reply_chance_failure_invalid_percent(self):
        self.mock_chat_config_dao.get.return_value = self.chat_config
        result, message = self.manager.change_chat_reply_chance("test_chat_id", 101)

        self.assertEqual(result, ChatConfigManager.Result.failure)
        self.assertIn("Invalid reply chance percent, must be in [0-100]", message)

    def test_change_chat_reply_chance_failure_chat_not_found(self):
        self.mock_chat_config_dao.get.return_value = None

        result, message = self.manager.change_chat_reply_chance("test_chat_id", 50)

        self.assertEqual(result, ChatConfigManager.Result.failure)
        self.assertIn("Chat 'test_chat_id' not found", message)

    def test_change_chat_reply_chance_failure_private_chat(self):
        private_chat_config = self.chat_config.model_copy(update = {"is_private": True})
        self.mock_chat_config_dao.get.return_value = private_chat_config

        result, message = self.manager.change_chat_reply_chance("test_chat_id", 50)

        self.assertEqual(result, ChatConfigManager.Result.failure)
        self.assertIn("Chat is private, reply chance cannot be changed", message)
        self.mock_chat_config_dao.get.assert_called_once_with("test_chat_id")

    def test_change_chat_release_notifications_success(self):
        self.mock_chat_config_dao.get.return_value = self.chat_config
        self.mock_chat_config_dao.save.return_value = self.chat_config

        result, message = self.manager.change_chat_release_notifications("test_chat_id", "major")

        self.assertEqual(result, ChatConfigManager.Result.success)
        self.assertIn("Release notifications are now set to major", message)
        self.mock_chat_config_dao.get.assert_called_once_with("test_chat_id")
        self.mock_chat_config_dao.save.assert_called()

    def test_change_chat_release_notifications_failure_invalid_selection(self):
        result, message = self.manager.change_chat_release_notifications("test_chat_id", "invalid_level")

        self.assertEqual(result, ChatConfigManager.Result.failure)
        self.assertIn("Invalid release notifications value 'invalid_level'", message)
        self.mock_chat_config_dao.get.assert_not_called()

    def test_change_chat_release_notifications_failure_empty_selection(self):
        result, message = self.manager.change_chat_release_notifications("test_chat_id", "")

        self.assertEqual(result, ChatConfigManager.Result.failure)
        self.assertIn("Invalid release notifications value ''", message)
        self.mock_chat_config_dao.get.assert_not_called()
