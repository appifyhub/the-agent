import unittest
from datetime import datetime

from db.model.user import UserDB
from db.schema.chat_config import ChatConfigSave
from db.schema.chat_message import ChatMessageSave
from db.schema.user import UserSave
from db.sql_util import SQLUtil


class ChatMessageCRUDTest(unittest.TestCase):
    __sql: SQLUtil

    def setUp(self):
        self.__sql = SQLUtil()

    def tearDown(self):
        self.__sql.end_session()

    def test_create_chat_message(self):
        chat = self.__sql.chat_config_crud().create(
            ChatConfigSave(chat_id = "chat1", persona_code = "persona1", persona_name = "Persona One")
        )
        user = self.__sql.user_crud().create(
            UserSave(
                full_name = "Test User",
                telegram_username = "test-user",
                telegram_chat_id = "123456",
                telegram_user_id = 123456,
                open_ai_key = "test-key",
                group = UserDB.Group.standard,
            )
        )
        chat_message_data = ChatMessageSave(
            chat_id = chat.chat_id,
            message_id = "msg1",
            author_id = user.id,
            sent_at = datetime.now(),
            text = "Hello, world!",
        )

        chat_message = self.__sql.chat_message_crud().create(chat_message_data)

        self.assertIsNotNone(chat_message.chat_id, chat_message_data.chat_id)
        self.assertEqual(chat_message.message_id, chat_message_data.message_id)
        self.assertEqual(chat_message.author_id, chat_message_data.author_id)
        self.assertEqual(chat_message.sent_at, chat_message_data.sent_at)
        self.assertEqual(chat_message.text, chat_message_data.text)

    def test_get_chat_message(self):
        chat = self.__sql.chat_config_crud().create(
            ChatConfigSave(chat_id = "chat1", persona_code = "persona1", persona_name = "Persona One")
        )
        user = self.__sql.user_crud().create(
            UserSave(
                full_name = "Test User",
                telegram_username = "test-user",
                telegram_chat_id = "123456",
                telegram_user_id = 123456,
                open_ai_key = "test-key",
                group = UserDB.Group.standard,
            )
        )
        chat_message_data = ChatMessageSave(
            chat_id = chat.chat_id,
            message_id = "msg1",
            author_id = user.id,
            sent_at = datetime.now(),
            text = "Hello, world!",
        )
        created_chat_message = self.__sql.chat_message_crud().create(chat_message_data)

        fetched_chat_message = self.__sql.chat_message_crud().get(
            created_chat_message.chat_id,
            created_chat_message.message_id
        )

        self.assertEqual(fetched_chat_message.chat_id, created_chat_message.chat_id)
        self.assertEqual(fetched_chat_message.message_id, created_chat_message.message_id)
        self.assertEqual(fetched_chat_message.author_id, created_chat_message.author_id)

    def test_get_all_chat_messages(self):
        chat1 = self.__sql.chat_config_crud().create(
            ChatConfigSave(chat_id = "chat1", persona_code = "persona1", persona_name = "Persona One")
        )
        chat2 = self.__sql.chat_config_crud().create(
            ChatConfigSave(chat_id = "chat2", persona_code = "persona2", persona_name = "Persona Two")
        )
        user = self.__sql.user_crud().create(
            UserSave(
                full_name = "Test User",
                telegram_username = "test-user",
                telegram_chat_id = "123456",
                telegram_user_id = 123456,
                open_ai_key = "test-key",
                group = UserDB.Group.standard,
            )
        )
        chat_messages = [
            self.__sql.chat_message_crud().create(
                ChatMessageSave(chat_id = chat1.chat_id, message_id = "msg1", author_id = user.id, text = "no1")
            ),
            self.__sql.chat_message_crud().create(
                ChatMessageSave(chat_id = chat2.chat_id, message_id = "msg2", author_id = user.id, text = "no2")
            ),
        ]

        fetched_chat_messages = self.__sql.chat_message_crud().get_all()

        self.assertEqual(len(fetched_chat_messages), len(chat_messages))
        for i in range(len(chat_messages)):
            self.assertEqual(fetched_chat_messages[i].chat_id, chat_messages[i].chat_id)
            self.assertEqual(fetched_chat_messages[i].message_id, chat_messages[i].message_id)
            self.assertEqual(fetched_chat_messages[i].author_id, chat_messages[i].author_id)

    def test_update_chat_message(self):
        chat = self.__sql.chat_config_crud().create(
            ChatConfigSave(chat_id = "chat1", persona_code = "persona1", persona_name = "Persona One")
        )
        user = self.__sql.user_crud().create(
            UserSave(
                full_name = "Test User",
                telegram_username = "test-user",
                telegram_chat_id = "123456",
                telegram_user_id = 123456,
                open_ai_key = "test-key",
                group = UserDB.Group.standard,
            )
        )
        chat_message_data = ChatMessageSave(
            chat_id = chat.chat_id,
            message_id = "msg1",
            author_id = user.id,
            sent_at = datetime.now(),
            text = "Hello, world!",
        )
        created_chat_message = self.__sql.chat_message_crud().create(chat_message_data)

        update_data = ChatMessageSave(
            chat_id = created_chat_message.chat_id,
            message_id = created_chat_message.message_id,
            text = "Updated! Hello, world!",
        )
        updated_chat_message = self.__sql.chat_message_crud().update(update_data)

        self.assertIsNotNone(updated_chat_message.chat_id, created_chat_message.chat_id)
        self.assertEqual(updated_chat_message.message_id, created_chat_message.message_id)
        self.assertEqual(updated_chat_message.author_id, created_chat_message.author_id)
        self.assertEqual(updated_chat_message.sent_at, created_chat_message.sent_at)
        self.assertEqual(updated_chat_message.text, update_data.text)

    def test_save_chat_message(self):
        chat = self.__sql.chat_config_crud().create(
            ChatConfigSave(chat_id = "chat1", persona_code = "persona1", persona_name = "Persona One")
        )
        user = self.__sql.user_crud().create(
            UserSave(
                full_name = "Test User",
                telegram_username = "test-user",
                telegram_chat_id = "123456",
                telegram_user_id = 123456,
                open_ai_key = "test-key",
                group = UserDB.Group.standard,
            )
        )
        chat_message_data = ChatMessageSave(
            chat_id = chat.chat_id,
            message_id = "msg1",
            author_id = user.id,
            sent_at = datetime.now(),
            text = "Hello, world!",
        )

        # First, save should create the record
        saved_chat_message = self.__sql.chat_message_crud().save(chat_message_data)
        self.assertIsNotNone(saved_chat_message)
        self.assertIsNotNone(saved_chat_message.sent_at)
        self.assertEqual(saved_chat_message.chat_id, chat_message_data.chat_id)
        self.assertEqual(saved_chat_message.message_id, chat_message_data.message_id)
        self.assertEqual(saved_chat_message.author_id, chat_message_data.author_id)
        self.assertEqual(saved_chat_message.text, chat_message_data.text)

        # Now, save should update the existing record
        update_data = ChatMessageSave(
            chat_id = saved_chat_message.chat_id,
            message_id = saved_chat_message.message_id,
            author_id = saved_chat_message.author_id,
            sent_at = saved_chat_message.sent_at,
            text = "Updated text!"
        )
        updated_chat_message = self.__sql.chat_message_crud().save(update_data)
        self.assertIsNotNone(updated_chat_message)
        self.assertEqual(updated_chat_message.chat_id, chat_message_data.chat_id)
        self.assertEqual(updated_chat_message.message_id, chat_message_data.message_id)
        self.assertEqual(updated_chat_message.sent_at, chat_message_data.sent_at)
        self.assertEqual(updated_chat_message.author_id, chat_message_data.author_id)
        self.assertEqual(updated_chat_message.text, update_data.text)

    def test_delete_chat_message(self):
        chat = self.__sql.chat_config_crud().create(
            ChatConfigSave(chat_id = "chat1", persona_code = "persona1", persona_name = "Persona One")
        )
        user = self.__sql.user_crud().create(
            UserSave(
                full_name = "Test User",
                telegram_username = "test-user",
                telegram_chat_id = "123456",
                telegram_user_id = 123456,
                open_ai_key = "test-key",
                group = UserDB.Group.standard,
            )
        )
        chat_message_data = ChatMessageSave(
            chat_id = chat.chat_id,
            message_id = "msg1",
            author_id = user.id,
            sent_at = datetime.now(),
            text = "Hello, world!",
        )
        created_chat_message = self.__sql.chat_message_crud().create(chat_message_data)

        deleted_chat_message = self.__sql.chat_message_crud().delete(
            created_chat_message.chat_id,
            created_chat_message.message_id,
        )

        self.assertEqual(deleted_chat_message.chat_id, created_chat_message.chat_id)
        self.assertEqual(deleted_chat_message.message_id, created_chat_message.message_id)
        self.assertIsNone(
            self.__sql.chat_message_crud().get(created_chat_message.chat_id, created_chat_message.message_id)
        )
