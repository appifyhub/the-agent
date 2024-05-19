import unittest

from db.schema.user import UserCreate, UserUpdate
from db.sql_util import SQLUtil


class TestUserCRUD(unittest.TestCase):
    sql: SQLUtil

    def setUp(self):
        self.sql = SQLUtil()

    def tearDown(self):
        self.sql.end_session()

    def test_create_user(self):
        user_data = UserCreate(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            open_ai_key = "test-key",
            group = "standard",
        )

        user = self.sql.user_crud().create(user_data)

        self.assertIsNotNone(user.id)
        self.assertEqual(user.full_name, user_data.full_name)
        self.assertEqual(user.telegram_username, user_data.telegram_username)
        self.assertEqual(user.telegram_chat_id, user_data.telegram_chat_id)
        self.assertEqual(user.open_ai_key, user_data.open_ai_key)
        self.assertEqual(user.group.value, user_data.group)
        self.assertIsNotNone(user.created_at)

    def test_get_user(self):
        user_data = UserCreate(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            open_ai_key = "test-key",
            group = "standard",
        )
        created_user = self.sql.user_crud().create(user_data)

        fetched_user = self.sql.user_crud().get(created_user.id)

        self.assertEqual(fetched_user.id, created_user.id)
        self.assertEqual(fetched_user.full_name, user_data.full_name)
        self.assertEqual(fetched_user.telegram_username, user_data.telegram_username)

    def test_get_all_users(self):
        users = [
            self.sql.user_crud().create(UserCreate()),
            self.sql.user_crud().create(UserCreate()),
        ]

        fetched_users = self.sql.user_crud().get_all()

        self.assertEqual(len(fetched_users), len(users))
        for i in range(len(users)):
            self.assertEqual(fetched_users[i].id, users[i].id)

    def test_update_user(self):
        user_data = UserCreate(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            open_ai_key = "test-key",
            group = "standard",
        )
        created_user = self.sql.user_crud().create(user_data)

        update_data = UserUpdate(
            full_name = "Updated User",
            telegram_username = "updated-user",
            telegram_chat_id = "654321",
            open_ai_key = "updated-key",
            group = "beta",
        )
        updated_user = self.sql.user_crud().update(created_user.id, update_data)

        self.assertEqual(updated_user.id, created_user.id)
        self.assertEqual(updated_user.full_name, update_data.full_name)
        self.assertEqual(updated_user.telegram_username, update_data.telegram_username)
        self.assertEqual(updated_user.telegram_chat_id, update_data.telegram_chat_id)
        self.assertEqual(updated_user.open_ai_key, update_data.open_ai_key)
        self.assertEqual(updated_user.group.value, update_data.group)
        self.assertEqual(updated_user.created_at, created_user.created_at)

    def test_delete_user(self):
        user_data = UserCreate(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            open_ai_key = "test-key",
            group = "standard",
        )
        created_user = self.sql.user_crud().create(user_data)

        deleted_user = self.sql.user_crud().delete(created_user.id)

        self.assertEqual(deleted_user.id, created_user.id)
        self.assertIsNone(self.sql.user_crud().get(created_user.id))
