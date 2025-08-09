import unittest
from uuid import UUID

from api.mapper.chat_mapper import domain_to_api
from db.model.chat_config import ChatConfigDB
from db.schema.chat_config import ChatConfig


class ChatMapperTest(unittest.TestCase):

    chat: ChatConfig

    def setUp(self):
        self.chat = ChatConfig(
            chat_id = UUID(int = 1),
            external_id = "12345",
            title = "Test Chat",
            language_iso_code = "en",
            language_name = "English",
            reply_chance_percent = 75,
            is_private = False,
            release_notifications = ChatConfigDB.ReleaseNotifications.major,
            chat_type = ChatConfigDB.ChatType.telegram,
        )

    def test_domain_to_api_conversion(self):
        api = domain_to_api(self.chat, is_own = True)

        self.assertEqual(api.chat_id, self.chat.chat_id.hex)
        self.assertEqual(api.title, self.chat.title)
        self.assertEqual(api.language_iso_code, self.chat.language_iso_code)
        self.assertEqual(api.language_name, self.chat.language_name)
        self.assertEqual(api.reply_chance_percent, self.chat.reply_chance_percent)
        self.assertEqual(api.release_notifications, self.chat.release_notifications.value)
        self.assertEqual(api.is_private, self.chat.is_private)
        self.assertTrue(api.is_own)
