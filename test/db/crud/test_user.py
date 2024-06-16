import unittest

from db.model.user import UserDB
from db.schema.user import UserSave
from db.sql_util import SQLUtil


class UserCRUDTest(unittest.TestCase):
    __sql: SQLUtil

    def setUp(self):
        self.__sql = SQLUtil()

    def tearDown(self):
        self.__sql.end_session()

    def test_create_user(self):
        user_data = UserSave(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            telegram_user_id = 123456,
            open_ai_key = "test-key",
            group = UserDB.Group.standard,
        )

        user = self.__sql.user_crud().create(user_data)

        self.assertIsNotNone(user.id)
        self.assertEqual(user.full_name, user_data.full_name)
        self.assertEqual(user.telegram_username, user_data.telegram_username)
        self.assertEqual(user.telegram_chat_id, user_data.telegram_chat_id)
        self.assertEqual(user.open_ai_key, user_data.open_ai_key)
        self.assertEqual(user.group.value, user_data.group.value)
        self.assertEqual(user.telegram_user_id, user_data.telegram_user_id)
        self.assertIsNotNone(user.created_at)

    def test_get_user(self):
        user_data = UserSave(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            telegram_user_id = 123456,
            open_ai_key = "test-key",
            group = UserDB.Group.standard,
        )
        created_user = self.__sql.user_crud().create(user_data)

        fetched_user = self.__sql.user_crud().get(created_user.id)

        self.assertEqual(fetched_user.id, created_user.id)
        self.assertEqual(fetched_user.full_name, user_data.full_name)
        self.assertEqual(fetched_user.telegram_username, user_data.telegram_username)
        self.assertEqual(fetched_user.telegram_user_id, user_data.telegram_user_id)

    def test_get_all_users(self):
        users = [
            self.__sql.user_crud().create(UserSave()),
            self.__sql.user_crud().create(UserSave()),
        ]

        fetched_users = self.__sql.user_crud().get_all()

        self.assertEqual(len(fetched_users), len(users))
        for i in range(len(users)):
            self.assertEqual(fetched_users[i].id, users[i].id)

    def test_get_user_by_telegram_user_id(self):
        user_data = UserSave(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            telegram_user_id = 55555,
            open_ai_key = "test-key",
            group = UserDB.Group.standard,
        )
        created_user = self.__sql.user_crud().create(user_data)

        fetched_user = self.__sql.user_crud().get_by_telegram_user_id(created_user.telegram_user_id)

        self.assertEqual(fetched_user.id, created_user.id)
        self.assertEqual(fetched_user.full_name, user_data.full_name)
        self.assertEqual(fetched_user.telegram_username, user_data.telegram_username)
        self.assertEqual(fetched_user.telegram_user_id, user_data.telegram_user_id)

    def test_update_user(self):
        user_data = UserSave(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            telegram_user_id = 123456,
            open_ai_key = "test-key",
            group = UserDB.Group.standard,
        )
        created_user = self.__sql.user_crud().create(user_data)

        update_data = UserSave(
            id = created_user.id,
            full_name = "Updated User",
            telegram_username = "updated-user",
            telegram_chat_id = "654321",
            telegram_user_id = 654321,
            open_ai_key = "updated-key",
            group = UserDB.Group.beta,
        )
        updated_user = self.__sql.user_crud().update(update_data)

        self.assertEqual(updated_user.id, created_user.id)
        self.assertEqual(updated_user.full_name, update_data.full_name)
        self.assertEqual(updated_user.telegram_username, update_data.telegram_username)
        self.assertEqual(updated_user.telegram_chat_id, update_data.telegram_chat_id)
        self.assertEqual(updated_user.open_ai_key, update_data.open_ai_key)
        self.assertEqual(updated_user.group.value, update_data.group.value)
        self.assertEqual(updated_user.telegram_user_id, update_data.telegram_user_id)
        self.assertEqual(updated_user.created_at, created_user.created_at)

    def test_save_user(self):
        user_data = UserSave(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            telegram_user_id = 123456,
            open_ai_key = "test-key",
            group = UserDB.Group.standard,
        )

        # First, save should create the record
        saved_user = self.__sql.user_crud().save(user_data)
        self.assertIsNotNone(saved_user)
        self.assertEqual(saved_user.full_name, user_data.full_name)
        self.assertEqual(saved_user.telegram_username, user_data.telegram_username)
        self.assertEqual(saved_user.telegram_chat_id, user_data.telegram_chat_id)
        self.assertEqual(saved_user.telegram_user_id, user_data.telegram_user_id)
        self.assertEqual(saved_user.open_ai_key, user_data.open_ai_key)
        self.assertEqual(saved_user.group.value, user_data.group.value)

        # Now, save should update the existing record
        update_data = UserSave(
            id = saved_user.id,
            full_name = "Updated User",
            telegram_username = "updated-user",
            telegram_chat_id = "654321",
            telegram_user_id = 654321,
            open_ai_key = "updated-key",
            group = UserDB.Group.beta,
        )
        updated_user = self.__sql.user_crud().save(update_data)
        self.assertIsNotNone(updated_user)
        self.assertEqual(updated_user.full_name, update_data.full_name)
        self.assertEqual(updated_user.telegram_username, update_data.telegram_username)
        self.assertEqual(updated_user.telegram_chat_id, update_data.telegram_chat_id)
        self.assertEqual(updated_user.telegram_user_id, update_data.telegram_user_id)
        self.assertEqual(updated_user.open_ai_key, update_data.open_ai_key)
        self.assertEqual(updated_user.group.value, update_data.group.value)

    def test_delete_user(self):
        user_data = UserSave(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            telegram_user_id = 123456,
            open_ai_key = "test-key",
            group = UserDB.Group.standard,
        )
        created_user = self.__sql.user_crud().create(user_data)

        deleted_user = self.__sql.user_crud().delete(created_user.id)

        self.assertEqual(deleted_user.id, created_user.id)
        self.assertIsNone(self.__sql.user_crud().get(created_user.id))
