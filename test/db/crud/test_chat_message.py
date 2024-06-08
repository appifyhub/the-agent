import unittest
from datetime import datetime

from db.schema.chat_config import ChatConfigCreate
from db.schema.chat_message import ChatMessageCreate, ChatMessageUpdate
from db.schema.user import UserCreate
from db.sql_util import SQLUtil


class TestChatMessageCRUD(unittest.TestCase):
    sql: SQLUtil

    def setUp(self):
        self.sql = SQLUtil()

    def tearDown(self):
        self.sql.end_session()

    def test_create_chat_message(self):
        chat = self.sql.chat_config_crud().create(
            ChatConfigCreate(chat_id = "chat1", persona_code = "persona1", persona_name = "Persona One")
        )
        user = self.sql.user_crud().create(
            UserCreate(
                full_name = "Test User",
                telegram_username = "test-user",
                telegram_chat_id = "123456",
                telegram_user_id = 123456,
                open_ai_key = "test-key",
                group = "standard",
            )
        )
        chat_message_data = ChatMessageCreate(
            chat_id = chat.chat_id,
            message_id = "msg1",
            author_id = user.id,
            sent_at = datetime.now(),
            text = "Hello, world!",
        )

        chat_message = self.sql.chat_message_crud().create(chat_message_data)

        self.assertIsNotNone(chat_message.chat_id, chat_message_data.chat_id)
        self.assertEqual(chat_message.message_id, chat_message_data.message_id)
        self.assertEqual(chat_message.author_id, chat_message_data.author_id)
        self.assertEqual(chat_message.sent_at, chat_message_data.sent_at)
        self.assertEqual(chat_message.text, chat_message_data.text)

    def test_get_chat_message(self):
        chat = self.sql.chat_config_crud().create(
            ChatConfigCreate(chat_id = "chat1", persona_code = "persona1", persona_name = "Persona One")
        )
        user = self.sql.user_crud().create(
            UserCreate(
                full_name = "Test User",
                telegram_username = "test-user",
                telegram_chat_id = "123456",
                telegram_user_id = 123456,
                open_ai_key = "test-key",
                group = "standard",
            )
        )
        chat_message_data = ChatMessageCreate(
            chat_id = chat.chat_id,
            message_id = "msg1",
            author_id = user.id,
            sent_at = datetime.now(),
            text = "Hello, world!",
        )
        created_chat_message = self.sql.chat_message_crud().create(chat_message_data)

        fetched_chat_message = self.sql.chat_message_crud().get(
            created_chat_message.chat_id,
            created_chat_message.message_id
        )

        self.assertEqual(fetched_chat_message.chat_id, created_chat_message.chat_id)
        self.assertEqual(fetched_chat_message.message_id, created_chat_message.message_id)
        self.assertEqual(fetched_chat_message.author_id, created_chat_message.author_id)

    def test_get_all_chat_messages(self):
        chat1 = self.sql.chat_config_crud().create(
            ChatConfigCreate(chat_id = "chat1", persona_code = "persona1", persona_name = "Persona One")
        )
        chat2 = self.sql.chat_config_crud().create(
            ChatConfigCreate(chat_id = "chat2", persona_code = "persona2", persona_name = "Persona Two")
        )
        user = self.sql.user_crud().create(
            UserCreate(
                full_name = "Test User",
                telegram_username = "test-user",
                telegram_chat_id = "123456",
                telegram_user_id = 123456,
                open_ai_key = "test-key",
                group = "standard",
            )
        )
        chat_messages = [
            self.sql.chat_message_crud().create(
                ChatMessageCreate(chat_id = chat1.chat_id, message_id = "msg1", author_id = user.id, text = "no1")
            ),
            self.sql.chat_message_crud().create(
                ChatMessageCreate(chat_id = chat2.chat_id, message_id = "msg2", author_id = user.id, text = "no2")
            ),
        ]

        fetched_chat_messages = self.sql.chat_message_crud().get_all()

        self.assertEqual(len(fetched_chat_messages), len(chat_messages))
        for i in range(len(chat_messages)):
            self.assertEqual(fetched_chat_messages[i].chat_id, chat_messages[i].chat_id)
            self.assertEqual(fetched_chat_messages[i].message_id, chat_messages[i].message_id)
            self.assertEqual(fetched_chat_messages[i].author_id, chat_messages[i].author_id)

    def test_update_chat_message(self):
        chat = self.sql.chat_config_crud().create(
            ChatConfigCreate(chat_id = "chat1", persona_code = "persona1", persona_name = "Persona One")
        )
        user = self.sql.user_crud().create(
            UserCreate(
                full_name = "Test User",
                telegram_username = "test-user",
                telegram_chat_id = "123456",
                telegram_user_id = 123456,
                open_ai_key = "test-key",
                group = "standard",
            )
        )
        chat_message_data = ChatMessageCreate(
            chat_id = chat.chat_id,
            message_id = "msg1",
            author_id = user.id,
            sent_at = datetime.now(),
            text = "Hello, world!",
        )
        created_chat_message = self.sql.chat_message_crud().create(chat_message_data)

        update_data = ChatMessageUpdate(
            text = "Updated! Hello, world!",
        )
        updated_chat_message = self.sql.chat_message_crud().update(
            created_chat_message.chat_id,
            created_chat_message.message_id,
            update_data,
        )

        self.assertIsNotNone(updated_chat_message.chat_id, created_chat_message.chat_id)
        self.assertEqual(updated_chat_message.message_id, created_chat_message.message_id)
        self.assertEqual(updated_chat_message.author_id, created_chat_message.author_id)
        self.assertEqual(updated_chat_message.sent_at, created_chat_message.sent_at)
        self.assertEqual(updated_chat_message.text, update_data.text)

    def test_delete_chat_message(self):
        chat = self.sql.chat_config_crud().create(
            ChatConfigCreate(chat_id = "chat1", persona_code = "persona1", persona_name = "Persona One")
        )
        user = self.sql.user_crud().create(
            UserCreate(
                full_name = "Test User",
                telegram_username = "test-user",
                telegram_chat_id = "123456",
                telegram_user_id = 123456,
                open_ai_key = "test-key",
                group = "standard",
            )
        )
        chat_message_data = ChatMessageCreate(
            chat_id = chat.chat_id,
            message_id = "msg1",
            author_id = user.id,
            sent_at = datetime.now(),
            text = "Hello, world!",
        )
        created_chat_message = self.sql.chat_message_crud().create(chat_message_data)

        deleted_chat_message = self.sql.chat_message_crud().delete(
            created_chat_message.chat_id,
            created_chat_message.message_id,
        )

        self.assertEqual(deleted_chat_message.chat_id, created_chat_message.chat_id)
        self.assertEqual(deleted_chat_message.message_id, created_chat_message.message_id)
        self.assertIsNone(
            self.sql.chat_message_crud().get(created_chat_message.chat_id, created_chat_message.message_id)
        )
