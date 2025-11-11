import unittest

from db.sql_util import SQLUtil
from pydantic import SecretStr

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
            whatsapp_user_id = "1234567890",
            whatsapp_phone_number = SecretStr("1234567890"),
            connect_key = "TEST-CONN-KEY1",
            open_ai_key = SecretStr("test-key"),
            anthropic_key = SecretStr("test-anthropic-key"),
            google_ai_key = SecretStr("test-google-ai-key"),
            perplexity_key = SecretStr("test-perplexity-key"),
            replicate_key = SecretStr("test-replicate-key"),
            rapid_api_key = SecretStr("test-rapid-api-key"),
            coinmarketcap_key = SecretStr("test-coinmarketcap-key"),
            tool_choice_chat = "gpt-4o",
            tool_choice_reasoning = "claude-3-7-sonnet-latest",
            tool_choice_copywriting = "gpt-4o-mini",
            tool_choice_vision = "gpt-4o",
            tool_choice_hearing = "whisper-1",
            tool_choice_images_gen = "dall-e-3",
            tool_choice_images_edit = "dall-e-2",
            tool_choice_images_restoration = "replicate-restoration",
            tool_choice_images_inpainting = "replicate-inpainting",
            tool_choice_images_background_removal = "replicate-bg-removal",
            tool_choice_search = "perplexity-search",
            tool_choice_embedding = "text-embedding-3-large",
            tool_choice_api_fiat_exchange = "rapid-api-fiat",
            tool_choice_api_crypto_exchange = "coinmarketcap-api",
            tool_choice_api_twitter = "rapid-api-twitter",
            group = UserDB.Group.standard,
        )

        user = self.sql.user_crud().create(user_data)

        self.assertIsNotNone(user.id)
        self.assertEqual(user.full_name, user_data.full_name)
        self.assertEqual(user.telegram_username, user_data.telegram_username)
        self.assertEqual(user.telegram_chat_id, user_data.telegram_chat_id)
        self.assertEqual(user.whatsapp_user_id, user_data.whatsapp_user_id)
        assert user_data.whatsapp_phone_number is not None
        self.assertEqual(user.whatsapp_phone_number, user_data.whatsapp_phone_number.get_secret_value())
        assert user_data.open_ai_key is not None
        self.assertEqual(user.open_ai_key, user_data.open_ai_key.get_secret_value())
        assert user_data.anthropic_key is not None
        self.assertEqual(user.anthropic_key, user_data.anthropic_key.get_secret_value())
        assert user_data.perplexity_key is not None
        self.assertEqual(user.perplexity_key, user_data.perplexity_key.get_secret_value())
        assert user_data.replicate_key is not None
        self.assertEqual(user.replicate_key, user_data.replicate_key.get_secret_value())
        assert user_data.rapid_api_key is not None
        self.assertEqual(user.rapid_api_key, user_data.rapid_api_key.get_secret_value())
        assert user_data.coinmarketcap_key is not None
        self.assertEqual(user.coinmarketcap_key, user_data.coinmarketcap_key.get_secret_value())
        self.assertEqual(user.tool_choice_chat, user_data.tool_choice_chat)
        self.assertEqual(user.tool_choice_reasoning, user_data.tool_choice_reasoning)
        self.assertEqual(user.tool_choice_copywriting, user_data.tool_choice_copywriting)
        self.assertEqual(user.tool_choice_vision, user_data.tool_choice_vision)
        self.assertEqual(user.tool_choice_hearing, user_data.tool_choice_hearing)
        self.assertEqual(user.tool_choice_images_gen, user_data.tool_choice_images_gen)
        self.assertEqual(user.tool_choice_images_edit, user_data.tool_choice_images_edit)
        self.assertEqual(user.tool_choice_images_restoration, user_data.tool_choice_images_restoration)
        self.assertEqual(user.tool_choice_images_inpainting, user_data.tool_choice_images_inpainting)
        self.assertEqual(user.tool_choice_images_background_removal, user_data.tool_choice_images_background_removal)
        self.assertEqual(user.tool_choice_search, user_data.tool_choice_search)
        self.assertEqual(user.tool_choice_embedding, user_data.tool_choice_embedding)
        self.assertEqual(user.tool_choice_api_fiat_exchange, user_data.tool_choice_api_fiat_exchange)
        self.assertEqual(user.tool_choice_api_crypto_exchange, user_data.tool_choice_api_crypto_exchange)
        self.assertEqual(user.tool_choice_api_twitter, user_data.tool_choice_api_twitter)
        self.assertEqual(user.group.value, user_data.group.value)
        self.assertEqual(user.telegram_user_id, user_data.telegram_user_id)
        self.assertIsNotNone(user.created_at)

    def test_get_user(self):
        user_data = UserSave(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            telegram_user_id = 123456,
            whatsapp_user_id = "1234567890",
            whatsapp_phone_number = SecretStr("1234567890"),
            connect_key = "TST2-KEY2-TST2",
            open_ai_key = SecretStr("test-key"),
            anthropic_key = SecretStr("test-anthropic-key"),
            perplexity_key = SecretStr("test-perplexity-key"),
            replicate_key = SecretStr("test-replicate-key"),
            rapid_api_key = SecretStr("test-rapid-api-key"),
            coinmarketcap_key = SecretStr("test-coinmarketcap-key"),
            tool_choice_chat = "gpt-4o",
            tool_choice_vision = "gpt-4o",
            group = UserDB.Group.standard,
        )
        created_user = self.sql.user_crud().create(user_data)

        fetched_user = self.sql.user_crud().get(created_user.id)

        assert fetched_user is not None
        self.assertEqual(fetched_user.id, created_user.id)
        self.assertEqual(fetched_user.full_name, user_data.full_name)
        self.assertEqual(fetched_user.telegram_username, user_data.telegram_username)
        self.assertEqual(fetched_user.telegram_user_id, user_data.telegram_user_id)
        self.assertEqual(fetched_user.whatsapp_user_id, user_data.whatsapp_user_id)
        assert user_data.whatsapp_phone_number is not None
        self.assertEqual(fetched_user.whatsapp_phone_number, user_data.whatsapp_phone_number.get_secret_value())
        self.assertEqual(fetched_user.tool_choice_chat, user_data.tool_choice_chat)
        self.assertEqual(fetched_user.tool_choice_vision, user_data.tool_choice_vision)

    def test_get_all_users(self):
        users = [
            self.sql.user_crud().create(UserSave(connect_key = "KEY1-KEY1-KEY1")),
            self.sql.user_crud().create(UserSave(connect_key = "KEY2-KEY2-KEY2")),
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
            connect_key = "USR1-KEY1-USR1",
            open_ai_key = SecretStr("test-key-1"),
            anthropic_key = SecretStr("test-anthropic-key-1"),
            perplexity_key = SecretStr("test-perplexity-key-1"),
            replicate_key = SecretStr("test-replicate-key-1"),
            rapid_api_key = SecretStr("test-rapid-api-key-1"),
            coinmarketcap_key = SecretStr("test-coinmarketcap-key-1"),
            tool_choice_chat = "gpt-4o",
            tool_choice_reasoning = "claude-3-7-sonnet-latest",
            group = UserDB.Group.standard,
        )
        user_data2 = UserSave(
            full_name = "Test User 2",
            telegram_username = "test-user-2",
            telegram_chat_id = "1234562",
            telegram_user_id = 1234562,
            connect_key = "USR2-KEY2-USR2",
            open_ai_key = SecretStr("test-key-2"),
            anthropic_key = SecretStr("test-anthropic-key-2"),
            perplexity_key = SecretStr("test-perplexity-key-2"),
            replicate_key = SecretStr("test-replicate-key-2"),
            rapid_api_key = SecretStr("test-rapid-api-key-2"),
            coinmarketcap_key = SecretStr("test-coinmarketcap-key-2"),
            tool_choice_vision = "gpt-4o",
            tool_choice_images_gen = "dall-e-3",
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
            connect_key = "TG5S-KEY5-TG5S",
            open_ai_key = SecretStr("test-key"),
            anthropic_key = SecretStr("test-anthropic-key"),
            perplexity_key = SecretStr("test-perplexity-key"),
            replicate_key = SecretStr("test-replicate-key"),
            rapid_api_key = SecretStr("test-rapid-api-key"),
            coinmarketcap_key = SecretStr("test-coinmarketcap-key"),
            tool_choice_hearing = "whisper-1",
            tool_choice_search = "perplexity-search",
            group = UserDB.Group.standard,
        )
        created_user = self.sql.user_crud().create(user_data)

        fetched_user = self.sql.user_crud().get_by_telegram_user_id(created_user.telegram_user_id)

        assert fetched_user is not None
        self.assertEqual(fetched_user.id, created_user.id)
        self.assertEqual(fetched_user.full_name, user_data.full_name)
        self.assertEqual(fetched_user.telegram_username, user_data.telegram_username)
        self.assertEqual(fetched_user.telegram_user_id, user_data.telegram_user_id)
        self.assertEqual(fetched_user.tool_choice_hearing, user_data.tool_choice_hearing)
        self.assertEqual(fetched_user.tool_choice_search, user_data.tool_choice_search)

    def test_get_user_by_telegram_username(self):
        user_data = UserSave(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            telegram_user_id = 55555,
            connect_key = "TG6S-KEY6-TG6S",
            open_ai_key = SecretStr("test-key"),
            anthropic_key = SecretStr("test-anthropic-key"),
            perplexity_key = SecretStr("test-perplexity-key"),
            replicate_key = SecretStr("test-replicate-key"),
            rapid_api_key = SecretStr("test-rapid-api-key"),
            coinmarketcap_key = SecretStr("test-coinmarketcap-key"),
            tool_choice_embedding = "text-embedding-3-large",
            tool_choice_api_twitter = "rapid-api-twitter",
            group = UserDB.Group.standard,
        )
        created_user = self.sql.user_crud().create(user_data)

        fetched_user = self.sql.user_crud().get_by_telegram_username(created_user.telegram_username)

        assert fetched_user is not None
        self.assertEqual(fetched_user.id, created_user.id)
        self.assertEqual(fetched_user.full_name, user_data.full_name)
        self.assertEqual(fetched_user.telegram_username, user_data.telegram_username)
        self.assertEqual(fetched_user.telegram_user_id, user_data.telegram_user_id)
        self.assertEqual(fetched_user.tool_choice_embedding, user_data.tool_choice_embedding)
        self.assertEqual(fetched_user.tool_choice_api_twitter, user_data.tool_choice_api_twitter)

    def test_get_user_by_whatsapp_user_id(self):
        user_data = UserSave(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            telegram_user_id = 55555,
            whatsapp_user_id = "9876543210",
            whatsapp_phone_number = SecretStr("9876543210"),
            connect_key = "WA7S-KEY7-WA7S",
            open_ai_key = SecretStr("test-key"),
            anthropic_key = SecretStr("test-anthropic-key"),
            perplexity_key = SecretStr("test-perplexity-key"),
            replicate_key = SecretStr("test-replicate-key"),
            rapid_api_key = SecretStr("test-rapid-api-key"),
            coinmarketcap_key = SecretStr("test-coinmarketcap-key"),
            tool_choice_hearing = "whisper-1",
            tool_choice_search = "perplexity-search",
            group = UserDB.Group.standard,
        )
        created_user = self.sql.user_crud().create(user_data)

        fetched_user = self.sql.user_crud().get_by_whatsapp_user_id(created_user.whatsapp_user_id)

        assert fetched_user is not None
        self.assertEqual(fetched_user.id, created_user.id)
        self.assertEqual(fetched_user.full_name, user_data.full_name)
        self.assertEqual(fetched_user.telegram_username, user_data.telegram_username)
        self.assertEqual(fetched_user.telegram_user_id, user_data.telegram_user_id)
        self.assertEqual(fetched_user.whatsapp_user_id, user_data.whatsapp_user_id)
        assert user_data.whatsapp_phone_number is not None
        self.assertEqual(fetched_user.whatsapp_phone_number, user_data.whatsapp_phone_number.get_secret_value())
        self.assertEqual(fetched_user.tool_choice_hearing, user_data.tool_choice_hearing)
        self.assertEqual(fetched_user.tool_choice_search, user_data.tool_choice_search)

    def test_get_user_by_whatsapp_phone_number(self):
        user_data = UserSave(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            telegram_user_id = 55555,
            whatsapp_user_id = "9876543210",
            whatsapp_phone_number = SecretStr("9876543210"),
            connect_key = "WA8S-KEY8-WA8S",
            open_ai_key = SecretStr("test-key"),
            anthropic_key = SecretStr("test-anthropic-key"),
            perplexity_key = SecretStr("test-perplexity-key"),
            replicate_key = SecretStr("test-replicate-key"),
            rapid_api_key = SecretStr("test-rapid-api-key"),
            coinmarketcap_key = SecretStr("test-coinmarketcap-key"),
            tool_choice_hearing = "whisper-1",
            tool_choice_search = "perplexity-search",
            group = UserDB.Group.standard,
        )
        created_user = self.sql.user_crud().create(user_data)

        fetched_user = self.sql.user_crud().get_by_whatsapp_phone_number("9876543210")

        assert fetched_user is not None
        self.assertEqual(fetched_user.id, created_user.id)
        self.assertEqual(fetched_user.full_name, user_data.full_name)
        self.assertEqual(fetched_user.telegram_username, user_data.telegram_username)
        self.assertEqual(fetched_user.telegram_chat_id, user_data.telegram_chat_id)
        self.assertEqual(fetched_user.telegram_user_id, user_data.telegram_user_id)
        self.assertEqual(fetched_user.whatsapp_user_id, user_data.whatsapp_user_id)
        assert user_data.whatsapp_phone_number is not None
        self.assertEqual(fetched_user.whatsapp_phone_number, user_data.whatsapp_phone_number.get_secret_value())

    def test_update_user(self):
        user_data = UserSave(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            telegram_user_id = 123456,
            whatsapp_user_id = "1234567890",
            whatsapp_phone_number = SecretStr("1234567890"),
            connect_key = "UPD9-KEY9-UPD9",
            open_ai_key = SecretStr("test-key"),
            anthropic_key = SecretStr("test-anthropic-key"),
            perplexity_key = SecretStr("test-perplexity-key"),
            replicate_key = SecretStr("test-replicate-key"),
            rapid_api_key = SecretStr("test-rapid-api-key"),
            coinmarketcap_key = SecretStr("test-coinmarketcap-key"),
            tool_choice_chat = "gpt-4o",
            tool_choice_reasoning = "claude-3-7-sonnet-latest",
            tool_choice_vision = "gpt-4o",
            group = UserDB.Group.standard,
        )
        created_user = self.sql.user_crud().create(user_data)

        update_data = UserSave(
            id = created_user.id,
            full_name = "Updated User",
            telegram_username = "updated-user",
            telegram_chat_id = "654321",
            telegram_user_id = 654321,
            whatsapp_user_id = "9876543210",
            whatsapp_phone_number = SecretStr("9876543210"),
            connect_key = "UPDA-KEYA-UPDA",
            open_ai_key = SecretStr("updated-key"),
            anthropic_key = SecretStr("updated-anthropic-key"),
            perplexity_key = SecretStr("updated-perplexity-key"),
            replicate_key = SecretStr("updated-replicate-key"),
            rapid_api_key = SecretStr("updated-rapid-api-key"),
            coinmarketcap_key = SecretStr("updated-coinmarketcap-key"),
            tool_choice_chat = "claude-3-7-sonnet-latest",
            tool_choice_reasoning = "gpt-4o",
            tool_choice_vision = "claude-3-7-sonnet-latest",
            tool_choice_hearing = "whisper-1",
            tool_choice_images_gen = "dall-e-3",
            group = UserDB.Group.developer,
        )
        updated_user = self.sql.user_crud().update(update_data)

        assert updated_user is not None
        self.assertEqual(updated_user.id, created_user.id)
        self.assertEqual(updated_user.full_name, update_data.full_name)
        self.assertEqual(updated_user.telegram_username, update_data.telegram_username)
        self.assertEqual(updated_user.telegram_chat_id, update_data.telegram_chat_id)
        self.assertEqual(updated_user.whatsapp_user_id, update_data.whatsapp_user_id)
        assert update_data.whatsapp_phone_number is not None
        self.assertEqual(updated_user.whatsapp_phone_number, update_data.whatsapp_phone_number.get_secret_value())
        assert update_data.open_ai_key is not None
        self.assertEqual(updated_user.open_ai_key, update_data.open_ai_key.get_secret_value())
        assert update_data.anthropic_key is not None
        self.assertEqual(updated_user.anthropic_key, update_data.anthropic_key.get_secret_value())
        assert update_data.perplexity_key is not None
        self.assertEqual(updated_user.perplexity_key, update_data.perplexity_key.get_secret_value())
        assert update_data.replicate_key is not None
        self.assertEqual(updated_user.replicate_key, update_data.replicate_key.get_secret_value())
        assert update_data.rapid_api_key is not None
        self.assertEqual(updated_user.rapid_api_key, update_data.rapid_api_key.get_secret_value())
        assert update_data.coinmarketcap_key is not None
        self.assertEqual(updated_user.coinmarketcap_key, update_data.coinmarketcap_key.get_secret_value())
        self.assertEqual(updated_user.tool_choice_chat, update_data.tool_choice_chat)
        self.assertEqual(updated_user.tool_choice_reasoning, update_data.tool_choice_reasoning)
        self.assertEqual(updated_user.tool_choice_vision, update_data.tool_choice_vision)
        self.assertEqual(updated_user.tool_choice_hearing, update_data.tool_choice_hearing)
        self.assertEqual(updated_user.tool_choice_images_gen, update_data.tool_choice_images_gen)
        self.assertEqual(updated_user.group.value, update_data.group.value)
        self.assertEqual(updated_user.telegram_user_id, update_data.telegram_user_id)
        self.assertEqual(updated_user.created_at, created_user.created_at)

    def test_save_user(self):
        user_data = UserSave(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            telegram_user_id = 123456,
            whatsapp_user_id = "1234567890",
            whatsapp_phone_number = SecretStr("1234567890"),
            connect_key = "SAVB-KEYB-SAVB",
            open_ai_key = SecretStr("test-key"),
            anthropic_key = SecretStr("test-anthropic-key"),
            perplexity_key = SecretStr("test-perplexity-key"),
            replicate_key = SecretStr("test-replicate-key"),
            rapid_api_key = SecretStr("test-rapid-api-key"),
            coinmarketcap_key = SecretStr("test-coinmarketcap-key"),
            tool_choice_copywriting = "gpt-4o-mini",
            tool_choice_images_edit = "dall-e-2",
            tool_choice_api_fiat_exchange = "rapid-api-fiat",
            group = UserDB.Group.standard,
        )

        # First, save should create the record
        saved_user = self.sql.user_crud().save(user_data)
        self.assertIsNotNone(saved_user)
        self.assertEqual(saved_user.full_name, user_data.full_name)
        self.assertEqual(saved_user.telegram_username, user_data.telegram_username)
        self.assertEqual(saved_user.telegram_chat_id, user_data.telegram_chat_id)
        self.assertEqual(saved_user.telegram_user_id, user_data.telegram_user_id)
        self.assertEqual(saved_user.whatsapp_user_id, user_data.whatsapp_user_id)
        assert user_data.whatsapp_phone_number is not None
        self.assertEqual(saved_user.whatsapp_phone_number, user_data.whatsapp_phone_number.get_secret_value())
        assert user_data.open_ai_key is not None
        self.assertEqual(saved_user.open_ai_key, user_data.open_ai_key.get_secret_value())
        assert user_data.anthropic_key is not None
        self.assertEqual(saved_user.anthropic_key, user_data.anthropic_key.get_secret_value())
        assert user_data.perplexity_key is not None
        self.assertEqual(saved_user.perplexity_key, user_data.perplexity_key.get_secret_value())
        assert user_data.replicate_key is not None
        self.assertEqual(saved_user.replicate_key, user_data.replicate_key.get_secret_value())
        assert user_data.rapid_api_key is not None
        self.assertEqual(saved_user.rapid_api_key, user_data.rapid_api_key.get_secret_value())
        assert user_data.coinmarketcap_key is not None
        self.assertEqual(saved_user.coinmarketcap_key, user_data.coinmarketcap_key.get_secret_value())
        self.assertEqual(saved_user.tool_choice_copywriting, user_data.tool_choice_copywriting)
        self.assertEqual(saved_user.tool_choice_images_edit, user_data.tool_choice_images_edit)
        self.assertEqual(saved_user.tool_choice_api_fiat_exchange, user_data.tool_choice_api_fiat_exchange)
        self.assertEqual(saved_user.group.value, user_data.group.value)

        # Now, save should update the existing record
        update_data = UserSave(
            id = saved_user.id,
            full_name = "Updated User",
            telegram_username = "updated-user",
            telegram_chat_id = "654321",
            telegram_user_id = 654321,
            whatsapp_user_id = "9876543210",
            whatsapp_phone_number = SecretStr("9876543210"),
            connect_key = "SAVC-KEYC-SAVC",
            open_ai_key = SecretStr("updated-key"),
            anthropic_key = SecretStr("updated-anthropic-key"),
            perplexity_key = SecretStr("updated-perplexity-key"),
            replicate_key = SecretStr("updated-replicate-key"),
            rapid_api_key = SecretStr("updated-rapid-api-key"),
            coinmarketcap_key = SecretStr("updated-coinmarketcap-key"),
            tool_choice_copywriting = "claude-3-7-sonnet-latest",
            tool_choice_images_edit = "dall-e-3",
            tool_choice_api_fiat_exchange = "updated-rapid-api-fiat",
            tool_choice_images_restoration = "replicate-restoration",
            tool_choice_api_crypto_exchange = "coinmarketcap-api",
            group = UserDB.Group.developer,
        )
        updated_user = self.sql.user_crud().save(update_data)
        self.assertIsNotNone(updated_user)
        self.assertEqual(updated_user.full_name, update_data.full_name)
        self.assertEqual(updated_user.telegram_username, update_data.telegram_username)
        self.assertEqual(updated_user.telegram_chat_id, update_data.telegram_chat_id)
        self.assertEqual(updated_user.telegram_user_id, update_data.telegram_user_id)
        self.assertEqual(updated_user.whatsapp_user_id, update_data.whatsapp_user_id)
        assert update_data.whatsapp_phone_number is not None
        self.assertEqual(updated_user.whatsapp_phone_number, update_data.whatsapp_phone_number.get_secret_value())
        assert update_data.open_ai_key is not None
        self.assertEqual(updated_user.open_ai_key, update_data.open_ai_key.get_secret_value())
        assert update_data.anthropic_key is not None
        self.assertEqual(updated_user.anthropic_key, update_data.anthropic_key.get_secret_value())
        assert update_data.perplexity_key is not None
        self.assertEqual(updated_user.perplexity_key, update_data.perplexity_key.get_secret_value())
        assert update_data.replicate_key is not None
        self.assertEqual(updated_user.replicate_key, update_data.replicate_key.get_secret_value())
        assert update_data.rapid_api_key is not None
        self.assertEqual(updated_user.rapid_api_key, update_data.rapid_api_key.get_secret_value())
        assert update_data.coinmarketcap_key is not None
        self.assertEqual(updated_user.coinmarketcap_key, update_data.coinmarketcap_key.get_secret_value())
        self.assertEqual(updated_user.tool_choice_copywriting, update_data.tool_choice_copywriting)
        self.assertEqual(updated_user.tool_choice_images_edit, update_data.tool_choice_images_edit)
        self.assertEqual(updated_user.tool_choice_api_fiat_exchange, update_data.tool_choice_api_fiat_exchange)
        self.assertEqual(updated_user.tool_choice_images_restoration, update_data.tool_choice_images_restoration)
        self.assertEqual(updated_user.tool_choice_api_crypto_exchange, update_data.tool_choice_api_crypto_exchange)
        self.assertEqual(updated_user.group.value, update_data.group.value)

    def test_delete_user(self):
        user_data = UserSave(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            telegram_user_id = 123456,
            whatsapp_user_id = "1234567890",
            whatsapp_phone_number = SecretStr("1234567890"),
            connect_key = "DELD-KEYD-DELD",
            open_ai_key = SecretStr("test-key"),
            anthropic_key = SecretStr("test-anthropic-key"),
            perplexity_key = SecretStr("test-perplexity-key"),
            replicate_key = SecretStr("test-replicate-key"),
            rapid_api_key = SecretStr("test-rapid-api-key"),
            coinmarketcap_key = SecretStr("test-coinmarketcap-key"),
            tool_choice_images_inpainting = "replicate-inpainting",
            tool_choice_images_background_removal = "replicate-bg-removal",
            group = UserDB.Group.standard,
        )
        created_user = self.sql.user_crud().create(user_data)

        deleted_user = self.sql.user_crud().delete(created_user.id)

        self.assertEqual(deleted_user.id, created_user.id)
        self.assertIsNone(self.sql.user_crud().get(created_user.id))

    def test_get_user_by_connect_key(self):
        user_data = UserSave(
            full_name = "Test User",
            telegram_username = "test-user",
            telegram_chat_id = "123456",
            telegram_user_id = 55555,
            whatsapp_user_id = "9876543210",
            whatsapp_phone_number = SecretStr("9876543210"),
            connect_key = "ABCD-EFGH-JKLM",
            open_ai_key = SecretStr("test-key"),
            anthropic_key = SecretStr("test-anthropic-key"),
            perplexity_key = SecretStr("test-perplexity-key"),
            replicate_key = SecretStr("test-replicate-key"),
            rapid_api_key = SecretStr("test-rapid-api-key"),
            coinmarketcap_key = SecretStr("test-coinmarketcap-key"),
            tool_choice_hearing = "whisper-1",
            tool_choice_search = "perplexity-search",
            group = UserDB.Group.standard,
        )
        created_user = self.sql.user_crud().create(user_data)

        fetched_user = self.sql.user_crud().get_by_connect_key("ABCD-EFGH-JKLM")

        assert fetched_user is not None
        self.assertEqual(fetched_user.id, created_user.id)
        self.assertEqual(fetched_user.full_name, user_data.full_name)
        self.assertEqual(fetched_user.connect_key, user_data.connect_key)
        self.assertEqual(fetched_user.telegram_username, user_data.telegram_username)
        self.assertEqual(fetched_user.telegram_user_id, user_data.telegram_user_id)
