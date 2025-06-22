import unittest

from db.sql_util import SQLUtil

from db.model.user import UserDB
from db.schema.user import UserSave


class UserCRUDTest(unittest.TestCase):
    sql: SQLUtil

    def setUp(self):
        self.sql = SQLUtil()

    def tearDown(self):
        self.sql.end_session()

    def test_create_user(self):
        user_data = UserSave(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            telegram_user_id = 123456,
            open_ai_key = "test-key",
            anthropic_key = "test-anthropic-key",
            perplexity_key = "test-perplexity-key",
            replicate_key = "test-replicate-key",
            rapid_api_key = "test-rapid-api-key",
            coinmarketcap_key = "test-coinmarketcap-key",
            group = UserDB.Group.standard,
        )

        user = self.sql.user_crud().create(user_data)

        self.assertIsNotNone(user.id)
        self.assertEqual(user.full_name, user_data.full_name)
        self.assertEqual(user.telegram_username, user_data.telegram_username)
        self.assertEqual(user.telegram_chat_id, user_data.telegram_chat_id)
        self.assertEqual(user.open_ai_key, user_data.open_ai_key)
        self.assertEqual(user.anthropic_key, user_data.anthropic_key)
        self.assertEqual(user.perplexity_key, user_data.perplexity_key)
        self.assertEqual(user.replicate_key, user_data.replicate_key)
        self.assertEqual(user.rapid_api_key, user_data.rapid_api_key)
        self.assertEqual(user.coinmarketcap_key, user_data.coinmarketcap_key)
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
            anthropic_key = "test-anthropic-key",
            perplexity_key = "test-perplexity-key",
            replicate_key = "test-replicate-key",
            rapid_api_key = "test-rapid-api-key",
            coinmarketcap_key = "test-coinmarketcap-key",
            group = UserDB.Group.standard,
        )
        created_user = self.sql.user_crud().create(user_data)

        fetched_user = self.sql.user_crud().get(created_user.id)

        self.assertEqual(fetched_user.id, created_user.id)
        self.assertEqual(fetched_user.full_name, user_data.full_name)
        self.assertEqual(fetched_user.telegram_username, user_data.telegram_username)
        self.assertEqual(fetched_user.telegram_user_id, user_data.telegram_user_id)

    def test_get_all_users(self):
        users = [
            self.sql.user_crud().create(UserSave()),
            self.sql.user_crud().create(UserSave()),
        ]

        fetched_users = self.sql.user_crud().get_all()

        self.assertEqual(len(fetched_users), len(users))
        for i in range(len(users)):
            self.assertEqual(fetched_users[i].id, users[i].id)

    def test_count_users(self):
        initial_count = self.sql.user_crud().count()
        self.assertEqual(initial_count, 0)

        user_data1 = UserSave(
            full_name = "Test User 1",
            telegram_username = "test-user-1",
            telegram_chat_id = "1234561",
            telegram_user_id = 1234561,
            open_ai_key = "test-key-1",
            anthropic_key = "test-anthropic-key-1",
            perplexity_key = "test-perplexity-key-1",
            replicate_key = "test-replicate-key-1",
            rapid_api_key = "test-rapid-api-key-1",
            coinmarketcap_key = "test-coinmarketcap-key-1",
            group = UserDB.Group.standard,
        )
        user_data2 = UserSave(
            full_name = "Test User 2",
            telegram_username = "test-user-2",
            telegram_chat_id = "1234562",
            telegram_user_id = 1234562,
            open_ai_key = "test-key-2",
            anthropic_key = "test-anthropic-key-2",
            perplexity_key = "test-perplexity-key-2",
            replicate_key = "test-replicate-key-2",
            rapid_api_key = "test-rapid-api-key-2",
            coinmarketcap_key = "test-coinmarketcap-key-2",
            group = UserDB.Group.standard,
        )
        self.sql.user_crud().create(user_data1)
        self.sql.user_crud().create(user_data2)

        user_count = self.sql.user_crud().count()
        self.assertEqual(user_count, 2)

    def test_get_user_by_telegram_user_id(self):
        user_data = UserSave(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            telegram_user_id = 55555,
            open_ai_key = "test-key",
            anthropic_key = "test-anthropic-key",
            perplexity_key = "test-perplexity-key",
            replicate_key = "test-replicate-key",
            rapid_api_key = "test-rapid-api-key",
            coinmarketcap_key = "test-coinmarketcap-key",
            group = UserDB.Group.standard,
        )
        created_user = self.sql.user_crud().create(user_data)

        fetched_user = self.sql.user_crud().get_by_telegram_user_id(created_user.telegram_user_id)

        self.assertEqual(fetched_user.id, created_user.id)
        self.assertEqual(fetched_user.full_name, user_data.full_name)
        self.assertEqual(fetched_user.telegram_username, user_data.telegram_username)
        self.assertEqual(fetched_user.telegram_user_id, user_data.telegram_user_id)

    def test_get_user_by_telegram_username(self):
        user_data = UserSave(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            telegram_user_id = 55555,
            open_ai_key = "test-key",
            anthropic_key = "test-anthropic-key",
            perplexity_key = "test-perplexity-key",
            replicate_key = "test-replicate-key",
            rapid_api_key = "test-rapid-api-key",
            coinmarketcap_key = "test-coinmarketcap-key",
            group = UserDB.Group.standard,
        )
        created_user = self.sql.user_crud().create(user_data)

        fetched_user = self.sql.user_crud().get_by_telegram_username(created_user.telegram_username)

        self.assertIsNotNone(fetched_user)
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
            anthropic_key = "test-anthropic-key",
            perplexity_key = "test-perplexity-key",
            replicate_key = "test-replicate-key",
            rapid_api_key = "test-rapid-api-key",
            coinmarketcap_key = "test-coinmarketcap-key",
            group = UserDB.Group.standard,
        )
        created_user = self.sql.user_crud().create(user_data)

        update_data = UserSave(
            id = created_user.id,
            full_name = "Updated User",
            telegram_username = "updated-user",
            telegram_chat_id = "654321",
            telegram_user_id = 654321,
            open_ai_key = "updated-key",
            anthropic_key = "updated-anthropic-key",
            perplexity_key = "updated-perplexity-key",
            replicate_key = "updated-replicate-key",
            rapid_api_key = "updated-rapid-api-key",
            coinmarketcap_key = "updated-coinmarketcap-key",
            group = UserDB.Group.developer,
        )
        updated_user = self.sql.user_crud().update(update_data)

        self.assertEqual(updated_user.id, created_user.id)
        self.assertEqual(updated_user.full_name, update_data.full_name)
        self.assertEqual(updated_user.telegram_username, update_data.telegram_username)
        self.assertEqual(updated_user.telegram_chat_id, update_data.telegram_chat_id)
        self.assertEqual(updated_user.open_ai_key, update_data.open_ai_key)
        self.assertEqual(updated_user.anthropic_key, update_data.anthropic_key)
        self.assertEqual(updated_user.perplexity_key, update_data.perplexity_key)
        self.assertEqual(updated_user.replicate_key, update_data.replicate_key)
        self.assertEqual(updated_user.rapid_api_key, update_data.rapid_api_key)
        self.assertEqual(updated_user.coinmarketcap_key, update_data.coinmarketcap_key)
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
            anthropic_key = "test-anthropic-key",
            perplexity_key = "test-perplexity-key",
            replicate_key = "test-replicate-key",
            rapid_api_key = "test-rapid-api-key",
            coinmarketcap_key = "test-coinmarketcap-key",
            group = UserDB.Group.standard,
        )

        # First, save should create the record
        saved_user = self.sql.user_crud().save(user_data)
        self.assertIsNotNone(saved_user)
        self.assertEqual(saved_user.full_name, user_data.full_name)
        self.assertEqual(saved_user.telegram_username, user_data.telegram_username)
        self.assertEqual(saved_user.telegram_chat_id, user_data.telegram_chat_id)
        self.assertEqual(saved_user.telegram_user_id, user_data.telegram_user_id)
        self.assertEqual(saved_user.open_ai_key, user_data.open_ai_key)
        self.assertEqual(saved_user.anthropic_key, user_data.anthropic_key)
        self.assertEqual(saved_user.perplexity_key, user_data.perplexity_key)
        self.assertEqual(saved_user.replicate_key, user_data.replicate_key)
        self.assertEqual(saved_user.rapid_api_key, user_data.rapid_api_key)
        self.assertEqual(saved_user.coinmarketcap_key, user_data.coinmarketcap_key)
        self.assertEqual(saved_user.group.value, user_data.group.value)

        # Now, save should update the existing record
        update_data = UserSave(
            id = saved_user.id,
            full_name = "Updated User",
            telegram_username = "updated-user",
            telegram_chat_id = "654321",
            telegram_user_id = 654321,
            open_ai_key = "updated-key",
            anthropic_key = "updated-anthropic-key",
            perplexity_key = "updated-perplexity-key",
            replicate_key = "updated-replicate-key",
            rapid_api_key = "updated-rapid-api-key",
            coinmarketcap_key = "updated-coinmarketcap-key",
            group = UserDB.Group.developer,
        )
        updated_user = self.sql.user_crud().save(update_data)
        self.assertIsNotNone(updated_user)
        self.assertEqual(updated_user.full_name, update_data.full_name)
        self.assertEqual(updated_user.telegram_username, update_data.telegram_username)
        self.assertEqual(updated_user.telegram_chat_id, update_data.telegram_chat_id)
        self.assertEqual(updated_user.telegram_user_id, update_data.telegram_user_id)
        self.assertEqual(updated_user.open_ai_key, update_data.open_ai_key)
        self.assertEqual(updated_user.anthropic_key, update_data.anthropic_key)
        self.assertEqual(updated_user.perplexity_key, update_data.perplexity_key)
        self.assertEqual(updated_user.replicate_key, update_data.replicate_key)
        self.assertEqual(updated_user.rapid_api_key, update_data.rapid_api_key)
        self.assertEqual(updated_user.coinmarketcap_key, update_data.coinmarketcap_key)
        self.assertEqual(updated_user.group.value, update_data.group.value)

    def test_delete_user(self):
        user_data = UserSave(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            telegram_user_id = 123456,
            open_ai_key = "test-key",
            anthropic_key = "test-anthropic-key",
            perplexity_key = "test-perplexity-key",
            replicate_key = "test-replicate-key",
            rapid_api_key = "test-rapid-api-key",
            coinmarketcap_key = "test-coinmarketcap-key",
            group = UserDB.Group.standard,
        )
        created_user = self.sql.user_crud().create(user_data)

        deleted_user = self.sql.user_crud().delete(created_user.id)

        self.assertEqual(deleted_user.id, created_user.id)
        self.assertIsNone(self.sql.user_crud().get(created_user.id))
