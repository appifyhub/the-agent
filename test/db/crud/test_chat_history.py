import unittest
from datetime import datetime

from db.schema.chat_config import ChatConfigCreate
from db.schema.chat_history import ChatHistoryCreate, ChatHistoryUpdate
from db.sql_util import SQLUtil


class TestChatHistoryCRUD(unittest.TestCase):
    sql: SQLUtil

    def setUp(self):
        self.sql = SQLUtil()

    def tearDown(self):
        self.sql.end_session()

    def test_create_chat_history(self):
        chat = self.sql.chat_config_crud().create(
            ChatConfigCreate(chat_id = "chat1", persona_code = "persona1", persona_name = "Persona One")
        )
        chat_history_data = ChatHistoryCreate(
            chat_id = chat.chat_id,
            message_id = "msg1",
            author_name = "Author",
            author_username = "author_username",
            sent_at = datetime.now(),
            text = "Hello, world!",
        )

        chat_history = self.sql.chat_history_crud().create(chat_history_data)

        self.assertIsNotNone(chat_history.chat_id, chat_history_data.chat_id)
        self.assertEqual(chat_history.message_id, chat_history_data.message_id)
        self.assertEqual(chat_history.author_name, chat_history_data.author_name)
        self.assertEqual(chat_history.author_username, chat_history_data.author_username)
        self.assertEqual(chat_history.sent_at, chat_history_data.sent_at)
        self.assertEqual(chat_history.text, chat_history_data.text)

    def test_get_chat_history(self):
        chat = self.sql.chat_config_crud().create(
            ChatConfigCreate(chat_id = "chat1", persona_code = "persona1", persona_name = "Persona One")
        )
        chat_history_data = ChatHistoryCreate(
            chat_id = chat.chat_id,
            message_id = "msg1",
            author_name = "Author",
            author_username = "author_username",
            sent_at = datetime.now(),
            text = "Hello, world!",
        )
        created_chat_history = self.sql.chat_history_crud().create(chat_history_data)

        fetched_chat_history = self.sql.chat_history_crud().get(
            created_chat_history.chat_id,
            created_chat_history.message_id
        )

        self.assertEqual(fetched_chat_history.chat_id, created_chat_history.chat_id)
        self.assertEqual(fetched_chat_history.message_id, created_chat_history.message_id)

    def test_get_all_chat_histories(self):
        chat1 = self.sql.chat_config_crud().create(
            ChatConfigCreate(chat_id = "chat1", persona_code = "persona1", persona_name = "Persona One")
        )
        chat2 = self.sql.chat_config_crud().create(
            ChatConfigCreate(chat_id = "chat2", persona_code = "persona2", persona_name = "Persona Two")
        )
        chat_histories = [
            self.sql.chat_history_crud().create(
                ChatHistoryCreate(chat_id = chat1.chat_id, message_id = "msg1", text = "no1")
            ),
            self.sql.chat_history_crud().create(
                ChatHistoryCreate(chat_id = chat2.chat_id, message_id = "msg2", text = "no2")
            ),
        ]

        fetched_chat_histories = self.sql.chat_history_crud().get_all()

        self.assertEqual(len(fetched_chat_histories), len(chat_histories))
        for i in range(len(chat_histories)):
            self.assertEqual(fetched_chat_histories[i].chat_id, chat_histories[i].chat_id)
            self.assertEqual(fetched_chat_histories[i].message_id, chat_histories[i].message_id)

    def test_update_chat_history(self):
        chat = self.sql.chat_config_crud().create(
            ChatConfigCreate(chat_id = "chat1", persona_code = "persona1", persona_name = "Persona One")
        )
        chat_history_data = ChatHistoryCreate(
            chat_id = chat.chat_id,
            message_id = "msg1",
            author_name = "Author",
            author_username = "author_username",
            sent_at = datetime.now(),
            text = "Hello, world!",
        )
        created_chat_history = self.sql.chat_history_crud().create(chat_history_data)

        update_data = ChatHistoryUpdate(
            text = "Updated! Hello, world!",
        )
        updated_chat_history = self.sql.chat_history_crud().update(
            created_chat_history.chat_id,
            created_chat_history.message_id,
            update_data,
        )

        self.assertIsNotNone(updated_chat_history.chat_id, created_chat_history.chat_id)
        self.assertEqual(updated_chat_history.message_id, created_chat_history.message_id)
        self.assertEqual(updated_chat_history.author_name, created_chat_history.author_name)
        self.assertEqual(updated_chat_history.author_username, created_chat_history.author_username)
        self.assertEqual(updated_chat_history.sent_at, created_chat_history.sent_at)
        self.assertEqual(updated_chat_history.text, update_data.text)

    def test_delete_chat_history(self):
        chat = self.sql.chat_config_crud().create(
            ChatConfigCreate(chat_id = "chat1", persona_code = "persona1", persona_name = "Persona One")
        )
        chat_history_data = ChatHistoryCreate(
            chat_id = chat.chat_id,
            message_id = "msg1",
            author_name = "Author",
            author_username = "author_username",
            sent_at = datetime.now(),
            text = "Hello, world!",
        )
        created_chat_history = self.sql.chat_history_crud().create(chat_history_data)

        deleted_chat_history = self.sql.chat_history_crud().delete(
            created_chat_history.chat_id,
            created_chat_history.message_id,
        )

        self.assertEqual(deleted_chat_history.chat_id, created_chat_history.chat_id)
        self.assertEqual(deleted_chat_history.message_id, created_chat_history.message_id)
        self.assertIsNone(
            self.sql.chat_history_crud().get(created_chat_history.chat_id, created_chat_history.message_id)
        )
