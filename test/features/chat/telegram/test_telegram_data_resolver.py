import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID

from db.sql_util import SQLUtil
from pydantic import SecretStr

from db.model.chat_config import ChatConfigDB
from db.model.user import UserDB
from db.schema.chat_config import ChatConfig, ChatConfigSave
from db.schema.chat_message import ChatMessage, ChatMessageSave
from db.schema.chat_message_attachment import ChatMessageAttachment, ChatMessageAttachmentSave
from db.schema.user import User, UserSave
from di.di import DI
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.chat.telegram.telegram_data_resolver import TelegramDataResolver
from features.chat.telegram.telegram_domain_mapper import TelegramDomainMapper
from features.integrations.integrations import resolve_agent_user
from util.config import config


class TelegramDataResolverTest(unittest.TestCase):

    agent_user: UserSave
    sql: SQLUtil
    mock_di: DI
    resolver: TelegramDataResolver

    def setUp(self):
        self.agent_user = resolve_agent_user(ChatConfigDB.ChatType.telegram)
        self.sql = SQLUtil()
        self.mock_di = Mock(spec = DI)
        # noinspection PyPropertyAccess
        self.mock_di.chat_config_crud = self.sql.chat_config_crud()
        # noinspection PyPropertyAccess
        self.mock_di.user_crud = self.sql.user_crud()
        # noinspection PyPropertyAccess
        self.mock_di.chat_message_crud = self.sql.chat_message_crud()
        # noinspection PyPropertyAccess
        self.mock_di.chat_message_attachment_crud = self.sql.chat_message_attachment_crud()
        # noinspection PyPropertyAccess
        self.mock_di.telegram_bot_api = MagicMock()
        # Ensure resolver uses a real SDK instance rather than an auto-created Mock
        # so that attachment refresh returns real models instead of Mock objects
        # noinspection PyPropertyAccess
        self.mock_di.telegram_bot_sdk = TelegramBotSDK(self.mock_di)
        self.resolver = TelegramDataResolver(self.mock_di)

    def tearDown(self):
        self.sql.end_session()

    def test_resolve_no_author(self):
        chat_config_data = ChatConfigSave(
            external_id = "c1",
            title = "Chat Title",
            is_private = True,
            chat_type = ChatConfigDB.ChatType.telegram,
        )
        message_data = ChatMessageSave(
            message_id = "m1",
            text = "This is a message",
        )
        attachment_data = ChatMessageAttachmentSave(
            id = "i1",
            message_id = message_data.message_id,
            last_url = "path/to/file.jpg",
            last_url_until = self.valid_url_timestamp(),
            extension = "jpg",
            mime_type = "image/jpeg",
        )
        mapping_result = TelegramDomainMapper.Result(
            chat = chat_config_data,
            author = None,
            message = message_data,
            attachments = [attachment_data],
        )

        result = self.resolver.resolve(mapping_result)

        self.assertIsNone(result.author)
        self.assertEqual(result.chat.external_id, chat_config_data.external_id)
        self.assertEqual(result.chat.is_private, chat_config_data.is_private)
        self.assertIsNone(result.author)
        self.assertEqual(result.message.chat_id, result.chat.chat_id)
        self.assertEqual(result.message.message_id, message_data.message_id)
        self.assertIsNone(result.message.author_id)
        self.assertEqual(result.attachments[0].id, attachment_data.id)
        self.assertEqual(result.attachments[0].message_id, attachment_data.message_id)
        self.assertEqual(result.attachments[0].chat_id, result.chat.chat_id)

    def test_resolve_with_author_bot(self):
        chat_config_data = ChatConfigSave(
            external_id = "c1",
            title = "Chat Title",
            is_private = True,
            chat_type = ChatConfigDB.ChatType.telegram,
        )
        author_data = UserSave(
            telegram_username = self.agent_user.telegram_username,
            telegram_chat_id = "c1",
            telegram_user_id = self.agent_user.telegram_user_id,
            full_name = self.agent_user.full_name,
        )
        message_data = ChatMessageSave(
            message_id = "m1",
            text = "This is a message",
        )
        attachment_data = ChatMessageAttachmentSave(
            id = "i1",
            message_id = message_data.message_id,
            last_url = "path/to/file.jpg",
            last_url_until = self.valid_url_timestamp(),
            extension = "jpg",
            mime_type = "image/jpeg",
        )
        mapping_result = TelegramDomainMapper.Result(
            chat = chat_config_data,
            author = author_data,
            message = message_data,
            attachments = [attachment_data],
        )

        result = self.resolver.resolve(mapping_result)

        assert result.author is not None
        self.assertIsNotNone(result.author.id)
        self.assertEqual(result.author.telegram_user_id, author_data.telegram_user_id)
        self.assertIsNone(result.author.telegram_chat_id)
        self.assertEqual(result.chat.external_id, chat_config_data.external_id)
        self.assertEqual(result.chat.is_private, chat_config_data.is_private)
        self.assertEqual(result.message.chat_id, result.chat.chat_id)
        self.assertEqual(result.message.message_id, message_data.message_id)
        self.assertIsNotNone(result.message.author_id)
        self.assertEqual(result.attachments[0].id, attachment_data.id)
        self.assertEqual(result.attachments[0].message_id, attachment_data.message_id)
        self.assertEqual(result.attachments[0].chat_id, result.chat.chat_id)

    def test_resolve_with_author_normal(self):
        chat_config_data = ChatConfigSave(
            external_id = "c1",
            title = "Chat Title",
            is_private = True,
            chat_type = ChatConfigDB.ChatType.telegram,
        )
        author_data = UserSave(
            telegram_username = "username",
            telegram_chat_id = "c1",
            telegram_user_id = 1,
            full_name = "New User",
        )
        message_data = ChatMessageSave(
            message_id = "m1",
            text = "This is a message",
        )
        attachment_data = ChatMessageAttachmentSave(
            id = "i1",
            message_id = message_data.message_id,
            last_url = "path/to/file.jpg",
            last_url_until = self.valid_url_timestamp(),
            extension = "jpg",
            mime_type = "image/jpeg",
        )
        mapping_result = TelegramDomainMapper.Result(
            chat = chat_config_data,
            author = author_data,
            message = message_data,
            attachments = [attachment_data],
        )

        result = self.resolver.resolve(mapping_result)

        assert result.author is not None
        self.assertIsNotNone(result.author.id)
        self.assertEqual(result.author.telegram_user_id, author_data.telegram_user_id)
        self.assertEqual(result.author.telegram_chat_id, chat_config_data.external_id)
        self.assertEqual(result.chat.external_id, chat_config_data.external_id)
        self.assertEqual(result.chat.is_private, chat_config_data.is_private)
        self.assertEqual(result.message.chat_id, result.chat.chat_id)
        self.assertEqual(result.message.message_id, message_data.message_id)
        self.assertIsNotNone(result.message.author_id)
        self.assertEqual(result.attachments[0].id, attachment_data.id)
        self.assertEqual(result.attachments[0].message_id, attachment_data.message_id)
        self.assertEqual(result.attachments[0].chat_id, result.chat.chat_id)

    def test_resolve_chat_config_existing(self):
        existing_config_data = ChatConfigSave(
            external_id = "c1",
            language_iso_code = "en",
            language_name = "English",
            title = "Old Title",
            is_private = False,
            reply_chance_percent = 100,
            release_notifications = ChatConfigDB.ReleaseNotifications.major,
            chat_type = ChatConfigDB.ChatType.telegram,
        )
        existing_config_db = self.sql.chat_config_crud().save(existing_config_data)
        existing_config = ChatConfig.model_validate(existing_config_db)

        mapped_data = ChatConfigSave(
            external_id = "c1",
            title = "New Title",
            is_private = True,
            chat_type = ChatConfigDB.ChatType.telegram,
        )

        result = self.resolver.resolve_chat_config(mapped_data)
        saved_config_db = self.sql.chat_config_crud().get(mapped_data.chat_id)
        saved_config = ChatConfig.model_validate(saved_config_db)

        self.assertEqual(result, saved_config)
        self.assertEqual(result.chat_id, mapped_data.chat_id)
        self.assertEqual(result.language_iso_code, existing_config.language_iso_code)
        self.assertEqual(result.language_name, existing_config.language_name)
        self.assertEqual(result.title, mapped_data.title)
        self.assertEqual(result.is_private, mapped_data.is_private)
        self.assertEqual(result.reply_chance_percent, mapped_data.reply_chance_percent)
        self.assertEqual(result.release_notifications, existing_config.release_notifications)

    def test_resolve_chat_config_new(self):
        mapped_data = ChatConfigSave(
            external_id = "c1",
            title = "Title",
            is_private = True,
            chat_type = ChatConfigDB.ChatType.telegram,
        )

        result = self.resolver.resolve_chat_config(mapped_data)
        saved_config_db = self.sql.chat_config_crud().get(result.chat_id)
        saved_config = ChatConfig.model_validate(saved_config_db)

        self.assertEqual(result, saved_config)
        # For new configs, chat_id is generated; mapped_data.chat_id remains None
        self.assertIsNone(mapped_data.chat_id)
        self.assertEqual(result.language_iso_code, mapped_data.language_iso_code)
        self.assertEqual(result.language_name, mapped_data.language_name)
        self.assertEqual(result.title, mapped_data.title)
        self.assertEqual(result.is_private, mapped_data.is_private)
        self.assertEqual(result.reply_chance_percent, mapped_data.reply_chance_percent)
        self.assertEqual(result.release_notifications, mapped_data.release_notifications)

    def test_resolve_author_none(self):
        result = self.resolver.resolve_author(None)
        self.assertIsNone(result)

    def test_resolve_author_new(self):
        mapped_data = UserSave(
            telegram_user_id = 1,
            full_name = "New User",
            telegram_chat_id = "c1",
        )

        result = self.resolver.resolve_author(mapped_data)
        saved_user_db = self.sql.user_crud().get_by_telegram_user_id(mapped_data.telegram_user_id or -1)
        saved_user = User.model_validate(saved_user_db)

        assert result is not None
        self.assertEqual(result, saved_user)
        self.assertIsNotNone(result.id)
        self.assertEqual(result.full_name, mapped_data.full_name)
        self.assertEqual(result.telegram_username, mapped_data.telegram_username)
        self.assertEqual(result.telegram_chat_id, mapped_data.telegram_chat_id)
        self.assertEqual(result.telegram_user_id, mapped_data.telegram_user_id)
        self.assertEqual(result.open_ai_key, mapped_data.open_ai_key)
        self.assertEqual(result.group, mapped_data.group)
        self.assertEqual(result.created_at, datetime.now().date())

    def test_resolve_author_by_username(self):
        existing_user_data = UserSave(
            telegram_user_id = None,
            telegram_username = "unique_username",
            full_name = "Existing User",
        )
        existing_user_db = self.sql.user_crud().save(existing_user_data)
        existing_user = User.model_validate(existing_user_db)

        mapped_data = UserSave(
            telegram_user_id = None,
            telegram_username = "unique_username",
            full_name = "Updated User",
            telegram_chat_id = "c1",
        )

        result = self.resolver.resolve_author(mapped_data)
        assert result is not None
        saved_user_db = self.sql.user_crud().get(result.id)
        saved_user = User.model_validate(saved_user_db)

        assert result is not None
        self.assertEqual(result, saved_user)
        self.assertEqual(result.id, existing_user.id)
        self.assertEqual(result.full_name, mapped_data.full_name)
        self.assertEqual(result.telegram_username, mapped_data.telegram_username)
        self.assertEqual(result.telegram_chat_id, mapped_data.telegram_chat_id)
        self.assertEqual(result.telegram_user_id, existing_user.telegram_user_id)
        self.assertEqual(result.open_ai_key, existing_user.open_ai_key)
        self.assertEqual(result.group, existing_user.group)
        self.assertEqual(result.created_at, existing_user.created_at)

    @patch("db.crud.user.UserCRUD.count")
    def test_resolve_author_user_limit_reached(self, mock_count):
        mock_count.return_value = config.max_users  # reach maximum immediately
        mapped_data = UserSave(
            telegram_user_id = 1,
            full_name = "New User",
            telegram_chat_id = "c1",
        )

        with self.assertRaises(ValueError) as context:
            self.resolver.resolve_author(mapped_data)

        self.assertEqual(str(context.exception), "User limit reached: 100/100. Try again later")
        mock_count.assert_called_once()

    def test_resolve_author_existing(self):
        existing_user_data = UserSave(
            telegram_user_id = 1,
            full_name = "Existing User",
            telegram_chat_id = "c1",
            open_ai_key = SecretStr("sk-key"),
            anthropic_key = SecretStr("sk-key"),
            perplexity_key = SecretStr("sk-key"),
            replicate_key = SecretStr("sk-key"),
            rapid_api_key = SecretStr("sk-key"),
            coinmarketcap_key = SecretStr("sk-key"),
            group = UserDB.Group.developer,
            # Add all tool choice fields to test preservation
            tool_choice_chat = "openai",
            tool_choice_reasoning = "anthropic",
            tool_choice_copywriting = "perplexity",
            tool_choice_vision = "openai",
            tool_choice_hearing = "openai",
            tool_choice_images_gen = "replicate",
            tool_choice_images_edit = "replicate",
            tool_choice_images_restoration = "replicate",
            tool_choice_images_inpainting = "replicate",
            tool_choice_images_background_removal = "replicate",
            tool_choice_search = "perplexity",
            tool_choice_embedding = "openai",
            tool_choice_api_fiat_exchange = "rapidapi",
            tool_choice_api_crypto_exchange = "coinmarketcap",
            tool_choice_api_twitter = "rapidapi",
        )
        existing_user_db = self.sql.user_crud().save(existing_user_data)
        existing_user = User.model_validate(existing_user_db)

        mapped_data = UserSave(
            telegram_user_id = 1,
            full_name = "Updated User",
            telegram_chat_id = "c2",
        )

        result = self.resolver.resolve_author(mapped_data)
        assert result is not None

        saved_user_db = self.sql.user_crud().get(result.id)
        saved_user = User.model_validate(saved_user_db)

        self.assertEqual(result, saved_user)
        self.assertEqual(result.id, existing_user.id)
        self.assertEqual(result.full_name, mapped_data.full_name)
        self.assertEqual(result.telegram_username, mapped_data.telegram_username)
        self.assertEqual(result.telegram_chat_id, mapped_data.telegram_chat_id)
        self.assertEqual(result.telegram_user_id, mapped_data.telegram_user_id)
        self.assertEqual(result.open_ai_key, existing_user.open_ai_key)
        self.assertEqual(result.anthropic_key, existing_user.anthropic_key)
        self.assertEqual(result.perplexity_key, existing_user.perplexity_key)
        self.assertEqual(result.replicate_key, existing_user.replicate_key)
        self.assertEqual(result.rapid_api_key, existing_user.rapid_api_key)
        self.assertEqual(result.coinmarketcap_key, existing_user.coinmarketcap_key)
        self.assertEqual(result.group, existing_user.group)
        self.assertEqual(result.created_at, existing_user.created_at)

        # Verify all tool choice fields are preserved from existing user
        self.assertEqual(result.tool_choice_chat, existing_user.tool_choice_chat)
        self.assertEqual(result.tool_choice_reasoning, existing_user.tool_choice_reasoning)
        self.assertEqual(result.tool_choice_copywriting, existing_user.tool_choice_copywriting)
        self.assertEqual(result.tool_choice_vision, existing_user.tool_choice_vision)
        self.assertEqual(result.tool_choice_hearing, existing_user.tool_choice_hearing)
        self.assertEqual(result.tool_choice_images_gen, existing_user.tool_choice_images_gen)
        self.assertEqual(result.tool_choice_images_edit, existing_user.tool_choice_images_edit)
        self.assertEqual(result.tool_choice_images_restoration, existing_user.tool_choice_images_restoration)
        self.assertEqual(result.tool_choice_images_inpainting, existing_user.tool_choice_images_inpainting)
        self.assertEqual(result.tool_choice_images_background_removal, existing_user.tool_choice_images_background_removal)
        self.assertEqual(result.tool_choice_search, existing_user.tool_choice_search)
        self.assertEqual(result.tool_choice_embedding, existing_user.tool_choice_embedding)
        self.assertEqual(result.tool_choice_api_fiat_exchange, existing_user.tool_choice_api_fiat_exchange)
        self.assertEqual(result.tool_choice_api_crypto_exchange, existing_user.tool_choice_api_crypto_exchange)
        self.assertEqual(result.tool_choice_api_twitter, existing_user.tool_choice_api_twitter)

    @patch("db.crud.user.UserCRUD.get_by_telegram_user_id")
    @patch("db.crud.user.UserCRUD.get_by_telegram_username")
    def test_resolve_author_api_key_reset(self, mock_get_by_username, mock_get_by_user_id):
        fake_user = User(
            id = UUID("123e4567-e89b-12d3-a456-426614174000"),
            full_name = "Existing User",
            telegram_username = "test_username",
            telegram_chat_id = "c1",
            telegram_user_id = 1,
            open_ai_key = None,
            anthropic_key = None,
            google_ai_key = None,
            perplexity_key = None,
            replicate_key = None,
            rapid_api_key = None,
            coinmarketcap_key = None,
            group = UserDB.Group.developer,
            created_at = datetime.now().date(),
        )

        mock_get_by_user_id.return_value = fake_user
        mock_get_by_username.return_value = None

        # Get all API key fields dynamically
        api_key_fields = User._get_secret_str_fields()

        # test the no-key behavior for all API keys
        mapped_data = UserSave(
            telegram_user_id = 1,
            full_name = "Test User",
            telegram_chat_id = "c1",
        )
        result = self.resolver.resolve_author(mapped_data)
        for field in api_key_fields:
            self.assertIsNone(getattr(result, field), f"{field} should remain None when already None")

        # test the empty key behavior for all API keys
        for field in api_key_fields:
            setattr(mapped_data, field, SecretStr(""))
            setattr(fake_user, field, SecretStr(""))
        result = self.resolver.resolve_author(mapped_data)
        for field in api_key_fields:
            self.assertIsNone(getattr(result, field), f"{field} should be reset to None if empty")

        # test the whitespace behavior for all API keys
        for field in api_key_fields:
            setattr(mapped_data, field, SecretStr("    "))
            setattr(fake_user, field, SecretStr("    "))
        result = self.resolver.resolve_author(mapped_data)
        for field in api_key_fields:
            self.assertIsNone(getattr(result, field), f"{field} should be reset to None if whitespace")

        # test the valid key behavior for all API keys
        for field in api_key_fields:
            setattr(mapped_data, field, SecretStr(f"valid_{field}"))
            setattr(fake_user, field, SecretStr(f"valid_{field}"))
        result = self.resolver.resolve_author(mapped_data)
        for field in api_key_fields:
            result_key = getattr(result, field)
            expected_key = result_key.get_secret_value() if result_key else None
            self.assertEqual(expected_key, f"valid_{field}", f"{field} should remain unchanged if valid")

    def test_resolve_author_tool_choice_cleanup(self):
        mapped_data = UserSave(
            telegram_user_id = 1,
            full_name = "Test User",
            telegram_chat_id = "c1",
            # Test various empty/whitespace scenarios for tool choice fields
            tool_choice_chat = "",  # empty string
            tool_choice_reasoning = "   ",  # whitespace
            tool_choice_copywriting = "perplexity",  # valid value
            tool_choice_vision = None,  # already None
        )

        result = self.resolver.resolve_author(mapped_data)
        assert result is not None
        # Empty string should be cleaned to None
        self.assertIsNone(result.tool_choice_chat, "Empty tool_choice_chat should be reset to None")
        # Whitespace should be cleaned to None
        self.assertIsNone(result.tool_choice_reasoning, "Whitespace tool_choice_reasoning should be reset to None")
        # Valid value should be preserved
        self.assertEqual(result.tool_choice_copywriting, "perplexity", "Valid tool_choice_copywriting should be preserved")
        # None should remain None
        self.assertIsNone(result.tool_choice_vision, "None tool_choice_vision should remain None")

    def test_resolve_chat_message_new(self):
        chat = self.sql.chat_config_crud().create(
            ChatConfigSave(external_id = "c1", chat_type = ChatConfigDB.ChatType.telegram),
        )
        mapped_data = ChatMessageSave(
            chat_id = chat.chat_id,
            message_id = "m1",
            text = "This is a message",
        )

        result = self.resolver.resolve_chat_message(mapped_data)
        saved_message_db = self.sql.chat_message_crud().get(mapped_data.chat_id, mapped_data.message_id)
        saved_message = ChatMessage.model_validate(saved_message_db)

        self.assertEqual(result, saved_message)
        self.assertEqual(result.chat_id, mapped_data.chat_id)
        self.assertEqual(result.message_id, mapped_data.message_id)
        self.assertEqual(result.author_id, mapped_data.author_id)
        self.assertEqual(result.sent_at, mapped_data.sent_at)
        self.assertEqual(result.text, mapped_data.text)

    def test_resolve_chat_message_with_existing(self):
        chat = self.sql.chat_config_crud().create(
            ChatConfigSave(external_id = "c1", chat_type = ChatConfigDB.ChatType.telegram),
        )
        old_message_data = ChatMessageSave(
            chat_id = chat.chat_id,
            message_id = "m1",
            author_id = None,
            sent_at = datetime.now() - timedelta(days = 1),
            text = "Old message",
        )
        self.sql.chat_message_crud().save(old_message_data)

        new_author_data = UserSave(full_name = "First Last", telegram_chat_id = "c1")
        new_author = User.model_validate(self.sql.user_crud().save(new_author_data))
        mapped_data = ChatMessageSave(
            chat_id = chat.chat_id,
            message_id = "m1",
            author_id = new_author.id,
            sent_at = datetime.now(),
            text = "Updated message",
        )

        result = self.resolver.resolve_chat_message(mapped_data)
        saved_message_db = self.sql.chat_message_crud().get(mapped_data.chat_id, mapped_data.message_id)
        saved_message = ChatMessage.model_validate(saved_message_db)

        self.assertEqual(result, saved_message)
        self.assertEqual(result.chat_id, mapped_data.chat_id)
        self.assertEqual(result.message_id, mapped_data.message_id)
        self.assertEqual(result.author_id, mapped_data.author_id)
        self.assertEqual(result.sent_at, mapped_data.sent_at)
        self.assertEqual(result.text, mapped_data.text)

    def test_resolve_chat_message_attachment_new(self):
        chat = self.sql.chat_config_crud().create(
            ChatConfigSave(external_id = "c1", chat_type = ChatConfigDB.ChatType.telegram),
        )
        self.sql.chat_message_crud().create(
            ChatMessageSave(chat_id = chat.chat_id, message_id = "m1", text = "x"),
        )
        mapped_data = ChatMessageAttachmentSave(
            id = "i1",
            chat_id = chat.chat_id,
            message_id = "m1",
            last_url = "path/to/file.jpg",
            last_url_until = self.valid_url_timestamp(),
            extension = "jpg",
            mime_type = "image/jpeg",
        )

        result = self.resolver.resolve_chat_message_attachment(mapped_data)
        saved_attachment_db = self.sql.chat_message_attachment_crud().get(str(mapped_data.id))
        saved_attachment = ChatMessageAttachment.model_validate(saved_attachment_db)

        self.assertEqual(result, saved_attachment)
        self.assertEqual(result.id, mapped_data.id)
        self.assertEqual(result.chat_id, mapped_data.chat_id)
        self.assertEqual(result.message_id, mapped_data.message_id)
        self.assertEqual(result.size, mapped_data.size)
        self.assertEqual(result.last_url, mapped_data.last_url)
        self.assertEqual(result.last_url_until, mapped_data.last_url_until)
        self.assertEqual(result.extension, mapped_data.extension)
        self.assertEqual(result.mime_type, mapped_data.mime_type)

    def test_resolve_chat_message_attachment_existing(self):
        chat = self.sql.chat_config_crud().create(
            ChatConfigSave(external_id = "c1", chat_type = ChatConfigDB.ChatType.telegram),
        )
        self.sql.chat_message_crud().create(
            ChatMessageSave(chat_id = chat.chat_id, message_id = "m1", text = "x"),
        )
        old_attachment_data = ChatMessageAttachmentSave(
            id = "i1",
            chat_id = chat.chat_id,
            message_id = "m1",
            size = 1,
            last_url = "path/to/file.jpg",
            last_url_until = self.valid_url_timestamp(),
            extension = "jpg",
            mime_type = "image/jpeg",
        )
        self.sql.chat_message_attachment_crud().save(old_attachment_data)

        mapped_data = ChatMessageAttachmentSave(id = "i1", chat_id = chat.chat_id, message_id = "m1")  # missing file data
        result = self.resolver.resolve_chat_message_attachment(mapped_data)  # injects file data from DB
        saved_attachment_db = self.sql.chat_message_attachment_crud().get(str(mapped_data.id))
        saved_attachment = ChatMessageAttachment.model_validate(saved_attachment_db)

        self.assertEqual(result, saved_attachment)
        self.assertEqual(result.id, mapped_data.id)
        self.assertEqual(result.chat_id, mapped_data.chat_id)
        self.assertEqual(result.message_id, mapped_data.message_id)
        self.assertEqual(result.size, old_attachment_data.size)
        self.assertEqual(result.last_url, old_attachment_data.last_url)
        self.assertEqual(result.last_url_until, old_attachment_data.last_url_until)
        self.assertEqual(result.extension, old_attachment_data.extension)
        self.assertEqual(result.mime_type, old_attachment_data.mime_type)

    @staticmethod
    def valid_url_timestamp():
        return int(datetime.now().timestamp()) + 10

    @staticmethod
    def expired_url_timestamp():
        return int(datetime.now().timestamp()) - 10
