import unittest

from db.sql_util import SQLUtil

from db.model.chat_config import ChatConfigDB
from db.schema.chat_config import ChatConfigSave


class ChatConfigCRUDTest(unittest.TestCase):

    sql: SQLUtil

    def setUp(self):
        self.sql = SQLUtil()

    def tearDown(self):
        self.sql.end_session()

    def test_create_chat_config(self):
        chat_config_data = ChatConfigSave(
            chat_id = "chat1",
            language_iso_code = "en",
            language_name = "English",
            title = "Chat One",
            is_private = True,
            reply_chance_percent = 100,
            release_notifications = ChatConfigDB.ReleaseNotifications.major,
        )

        chat_config = self.sql.chat_config_crud().create(chat_config_data)

        self.assertEqual(chat_config.chat_id, chat_config_data.chat_id)
        self.assertEqual(chat_config.language_iso_code, chat_config_data.language_iso_code)
        self.assertEqual(chat_config.language_name, chat_config_data.language_name)
        self.assertEqual(chat_config.title, chat_config_data.title)
        self.assertEqual(chat_config.is_private, chat_config_data.is_private)
        self.assertEqual(chat_config.reply_chance_percent, chat_config_data.reply_chance_percent)
        self.assertEqual(chat_config.release_notifications, chat_config_data.release_notifications)

    def test_get_chat_config(self):
        chat_config_data = ChatConfigSave(
            chat_id = "chat1",
            language_iso_code = "en",
            language_name = "English",
            title = "Chat One",
            is_private = True,
            reply_chance_percent = 100,
            release_notifications = ChatConfigDB.ReleaseNotifications.major,
        )
        created_chat_config = self.sql.chat_config_crud().create(chat_config_data)

        fetched_chat_config = self.sql.chat_config_crud().get(created_chat_config.chat_id)

        self.assertEqual(fetched_chat_config.chat_id, created_chat_config.chat_id)

    def test_get_all_chat_configs(self):
        chat_configs = [
            self.sql.chat_config_crud().create(
                ChatConfigSave(chat_id = "chat1"),
            ),
            self.sql.chat_config_crud().create(
                ChatConfigSave(chat_id = "chat2"),
            ),
        ]

        fetched_chat_configs = self.sql.chat_config_crud().get_all()

        self.assertEqual(len(fetched_chat_configs), len(chat_configs))
        for i in range(len(chat_configs)):
            self.assertEqual(fetched_chat_configs[i].chat_id, chat_configs[i].chat_id)

    def test_update_chat_config(self):
        chat_config_data = ChatConfigSave(
            chat_id = "chat1",
            language_iso_code = "en",
            language_name = "English",
            title = "Chat One",
            is_private = True,
            reply_chance_percent = 100,
            release_notifications = ChatConfigDB.ReleaseNotifications.major,
        )
        created_chat_config = self.sql.chat_config_crud().create(chat_config_data)

        update_data = ChatConfigSave(
            chat_id = created_chat_config.chat_id,
            language_iso_code = "fr",
            language_name = "French",
            title = "Chat Another",
            is_private = False,
            reply_chance_percent = 0,
            release_notifications = ChatConfigDB.ReleaseNotifications.minor,
        )
        updated_chat_config = self.sql.chat_config_crud().update(update_data)

        self.assertEqual(updated_chat_config.chat_id, created_chat_config.chat_id)
        self.assertEqual(updated_chat_config.language_iso_code, update_data.language_iso_code)
        self.assertEqual(updated_chat_config.language_name, update_data.language_name)
        self.assertEqual(updated_chat_config.title, update_data.title)
        self.assertEqual(updated_chat_config.is_private, update_data.is_private)
        self.assertEqual(updated_chat_config.reply_chance_percent, update_data.reply_chance_percent)

    def test_save_chat_config(self):
        chat_config_data = ChatConfigSave(
            chat_id = "chat1",
            language_iso_code = "en",
            language_name = "English",
            title = "Chat One",
            is_private = True,
            reply_chance_percent = 100,
            release_notifications = ChatConfigDB.ReleaseNotifications.major,
        )

        # First, save should create the record
        saved_chat_config = self.sql.chat_config_crud().save(chat_config_data)
        self.assertIsNotNone(saved_chat_config)
        self.assertEqual(saved_chat_config.chat_id, chat_config_data.chat_id)
        self.assertEqual(saved_chat_config.language_iso_code, chat_config_data.language_iso_code)
        self.assertEqual(saved_chat_config.language_name, chat_config_data.language_name)
        self.assertEqual(saved_chat_config.title, chat_config_data.title)
        self.assertEqual(saved_chat_config.is_private, chat_config_data.is_private)
        self.assertEqual(saved_chat_config.reply_chance_percent, chat_config_data.reply_chance_percent)
        self.assertEqual(saved_chat_config.release_notifications, chat_config_data.release_notifications)

        # Now, save should update the existing record
        update_data = ChatConfigSave(
            chat_id = saved_chat_config.chat_id,
            language_iso_code = "fr",
            language_name = "French",
            title = "Chat Another",
            is_private = False,
            reply_chance_percent = 0,
            release_notifications = ChatConfigDB.ReleaseNotifications.minor,
        )
        updated_chat_config = self.sql.chat_config_crud().save(update_data)
        self.assertIsNotNone(updated_chat_config)
        self.assertEqual(updated_chat_config.chat_id, saved_chat_config.chat_id)
        self.assertEqual(updated_chat_config.language_iso_code, update_data.language_iso_code)
        self.assertEqual(updated_chat_config.language_name, update_data.language_name)
        self.assertEqual(updated_chat_config.title, update_data.title)
        self.assertEqual(updated_chat_config.is_private, update_data.is_private)
        self.assertEqual(updated_chat_config.reply_chance_percent, update_data.reply_chance_percent)
        self.assertEqual(updated_chat_config.release_notifications, update_data.release_notifications)

    def test_delete_chat_config(self):
        chat_config_data = ChatConfigSave(chat_id = "chat1")
        created_chat_config = self.sql.chat_config_crud().create(chat_config_data)

        deleted_chat_config = self.sql.chat_config_crud().delete(created_chat_config.chat_id)

        self.assertEqual(deleted_chat_config.chat_id, created_chat_config.chat_id)
        self.assertIsNone(self.sql.chat_config_crud().get(created_chat_config.chat_id))
