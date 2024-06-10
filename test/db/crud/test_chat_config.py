import unittest

from db.schema.chat_config import ChatConfigSave
from db.sql_util import SQLUtil


class TestChatConfigCRUD(unittest.TestCase):
    sql: SQLUtil

    def setUp(self):
        self.sql = SQLUtil()

    def tearDown(self):
        self.sql.end_session()

    def test_create_chat_config(self):
        chat_config_data = ChatConfigSave(
            chat_id = "chat1",
            persona_code = "persona1",
            persona_name = "Persona One",
            language_iso_code = "en",
            language_name = "English",
            title = "Chat One",
            is_private = True,
        )

        chat_config = self.sql.chat_config_crud().create(chat_config_data)

        self.assertEqual(chat_config.chat_id, chat_config_data.chat_id)
        self.assertEqual(chat_config.persona_code, chat_config_data.persona_code)
        self.assertEqual(chat_config.persona_name, chat_config_data.persona_name)
        self.assertEqual(chat_config.language_iso_code, chat_config_data.language_iso_code)
        self.assertEqual(chat_config.language_name, chat_config_data.language_name)

    def test_get_chat_config(self):
        chat_config_data = ChatConfigSave(
            chat_id = "chat1",
            persona_code = "persona1",
            persona_name = "Persona One",
            language_iso_code = "en",
            language_name = "English",
            title = "Chat One",
            is_private = True,
        )
        created_chat_config = self.sql.chat_config_crud().create(chat_config_data)

        fetched_chat_config = self.sql.chat_config_crud().get(created_chat_config.chat_id)

        self.assertEqual(fetched_chat_config.chat_id, created_chat_config.chat_id)
        self.assertEqual(fetched_chat_config.persona_code, chat_config_data.persona_code)
        self.assertEqual(fetched_chat_config.persona_name, chat_config_data.persona_name)

    def test_get_all_chat_configs(self):
        chat_configs = [
            self.sql.chat_config_crud().create(
                ChatConfigSave(chat_id = "chat1", persona_code = "persona1", persona_name = "Persona One")
            ),
            self.sql.chat_config_crud().create(
                ChatConfigSave(chat_id = "chat2", persona_code = "persona2", persona_name = "Persona Two")
            ),
        ]

        fetched_chat_configs = self.sql.chat_config_crud().get_all()

        self.assertEqual(len(fetched_chat_configs), len(chat_configs))
        for i in range(len(chat_configs)):
            self.assertEqual(fetched_chat_configs[i].chat_id, chat_configs[i].chat_id)

    def test_update_chat_config(self):
        chat_config_data = ChatConfigSave(
            chat_id = "chat1",
            persona_code = "persona1",
            persona_name = "Persona One",
            language_iso_code = "en",
            language_name = "English",
            title = "Chat One",
            is_private = True,
        )
        created_chat_config = self.sql.chat_config_crud().create(chat_config_data)

        update_data = ChatConfigSave(
            chat_id = created_chat_config.chat_id,
            persona_code = "persona2",
            persona_name = "Persona Two",
            language_iso_code = "fr",
            language_name = "French",
            title = "Chat Another",
            is_private = False,
        )
        updated_chat_config = self.sql.chat_config_crud().update(update_data)

        self.assertEqual(updated_chat_config.chat_id, created_chat_config.chat_id)
        self.assertEqual(updated_chat_config.persona_code, created_chat_config.persona_code)
        self.assertEqual(updated_chat_config.persona_name, update_data.persona_name)
        self.assertEqual(updated_chat_config.language_iso_code, update_data.language_iso_code)
        self.assertEqual(updated_chat_config.language_name, update_data.language_name)

    def test_save_chat_config(self):
        chat_config_data = ChatConfigSave(
            chat_id = "chat1",
            persona_code = "persona1",
            persona_name = "Persona One",
            language_iso_code = "en",
            language_name = "English",
            title = "Chat One",
            is_private = True,
        )

        # First, save should create the record
        saved_chat_config = self.sql.chat_config_crud().save(chat_config_data)
        self.assertIsNotNone(saved_chat_config)
        self.assertEqual(saved_chat_config.chat_id, chat_config_data.chat_id)
        self.assertEqual(saved_chat_config.persona_code, chat_config_data.persona_code)
        self.assertEqual(saved_chat_config.persona_name, chat_config_data.persona_name)
        self.assertEqual(saved_chat_config.language_iso_code, chat_config_data.language_iso_code)
        self.assertEqual(saved_chat_config.language_name, chat_config_data.language_name)

        # Now, save should update the existing record
        update_data = ChatConfigSave(
            chat_id = saved_chat_config.chat_id,
            persona_code = "persona2",
            persona_name = "Persona Two",
            language_iso_code = "fr",
            language_name = "French",
            title = "Chat Another",
            is_private = False,
        )
        updated_chat_config = self.sql.chat_config_crud().save(update_data)
        self.assertIsNotNone(updated_chat_config)
        self.assertEqual(updated_chat_config.chat_id, saved_chat_config.chat_id)
        self.assertEqual(updated_chat_config.persona_code, update_data.persona_code)
        self.assertEqual(updated_chat_config.persona_name, update_data.persona_name)
        self.assertEqual(updated_chat_config.language_iso_code, update_data.language_iso_code)
        self.assertEqual(updated_chat_config.language_name, update_data.language_name)

    def test_delete_chat_config(self):
        chat_config_data = ChatConfigSave(chat_id = "chat1")
        created_chat_config = self.sql.chat_config_crud().create(chat_config_data)

        deleted_chat_config = self.sql.chat_config_crud().delete(created_chat_config.chat_id)

        self.assertEqual(deleted_chat_config.chat_id, created_chat_config.chat_id)
        self.assertIsNone(self.sql.chat_config_crud().get(created_chat_config.chat_id))
