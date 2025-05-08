import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID
from db.model.user import UserDB
from db.schema.chat_config import ChatConfigSave, ChatConfig
from db.schema.chat_message import ChatMessageSave, ChatMessage
from db.schema.chat_message_attachment import ChatMessageAttachmentSave, ChatMessageAttachment
from db.schema.user import UserSave, User
from db.sql_util import SQLUtil
from features.chat.telegram.sdk.telegram_bot_api import TelegramBotAPI
from features.chat.telegram.telegram_data_resolver import TelegramDataResolver
from features.chat.telegram.telegram_domain_mapper import TelegramDomainMapper
from features.prompting.prompt_library import TELEGRAM_BOT_USER
from util.config import config


class TelegramDataResolverTest(unittest.TestCase):
    sql: SQLUtil
    bot_api: TelegramBotAPI
    resolver: TelegramDataResolver

    def setUp(self):
        config.verbose = True
        self.sql = SQLUtil()
        self.bot_api = MagicMock()
        self.resolver = TelegramDataResolver(self.sql.get_session(), self.bot_api)

    def tearDown(self):
        self.sql.end_session()

    def test_resolve_no_author(self):
        chat_config_data = ChatConfigSave(chat_id = "c1", title = "Chat Title", is_private = True)
        message_data = ChatMessageSave(
            chat_id = chat_config_data.chat_id,
            message_id = "m1",
            text = "This is a message",
        )
        attachment_data = ChatMessageAttachmentSave(
            id = "i1",
            chat_id = chat_config_data.chat_id,
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
        self.assertEqual(result.chat.chat_id, chat_config_data.chat_id)
        self.assertEqual(result.chat.is_private, chat_config_data.is_private)
        self.assertIsNone(result.author)
        self.assertEqual(result.message.chat_id, message_data.chat_id)
        self.assertEqual(result.message.message_id, message_data.message_id)
        self.assertIsNone(result.message.author_id)
        self.assertEqual(result.attachments[0].id, attachment_data.id)
        self.assertEqual(result.attachments[0].message_id, attachment_data.message_id)
        self.assertEqual(result.attachments[0].chat_id, attachment_data.chat_id)

    def test_resolve_with_author_bot(self):
        chat_config_data = ChatConfigSave(chat_id = "c1", title = "Chat Title", is_private = True)
        author_data = UserSave(
            telegram_username = TELEGRAM_BOT_USER.telegram_username,
            telegram_chat_id = chat_config_data.chat_id,
            telegram_user_id = TELEGRAM_BOT_USER.telegram_user_id,
            full_name = TELEGRAM_BOT_USER.full_name,
        )
        message_data = ChatMessageSave(
            chat_id = chat_config_data.chat_id,
            message_id = "m1",
            text = "This is a message",
        )
        attachment_data = ChatMessageAttachmentSave(
            id = "i1",
            chat_id = chat_config_data.chat_id,
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

        self.assertIsNotNone(result.author.id)
        self.assertEqual(result.chat.chat_id, chat_config_data.chat_id)
        self.assertEqual(result.chat.is_private, chat_config_data.is_private)
        self.assertEqual(result.author.telegram_user_id, author_data.telegram_user_id)
        self.assertIsNone(result.author.telegram_chat_id)
        self.assertEqual(result.message.chat_id, message_data.chat_id)
        self.assertEqual(result.message.message_id, message_data.message_id)
        self.assertIsNotNone(result.message.author_id)
        self.assertEqual(result.attachments[0].id, attachment_data.id)
        self.assertEqual(result.attachments[0].message_id, attachment_data.message_id)
        self.assertEqual(result.attachments[0].chat_id, attachment_data.chat_id)

    def test_resolve_with_author_normal(self):
        chat_config_data = ChatConfigSave(chat_id = "c1", title = "Chat Title", is_private = True)
        author_data = UserSave(
            telegram_username = "username",
            telegram_chat_id = chat_config_data.chat_id,
            telegram_user_id = 1,
            full_name = "New User",
        )
        message_data = ChatMessageSave(
            chat_id = chat_config_data.chat_id,
            message_id = "m1",
            text = "This is a message",
        )
        attachment_data = ChatMessageAttachmentSave(
            id = "i1",
            chat_id = chat_config_data.chat_id,
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

        self.assertIsNotNone(result.author.id)
        self.assertEqual(result.chat.chat_id, chat_config_data.chat_id)
        self.assertEqual(result.chat.is_private, chat_config_data.is_private)
        self.assertEqual(result.author.telegram_user_id, author_data.telegram_user_id)
        self.assertEqual(result.author.telegram_chat_id, chat_config_data.chat_id)
        self.assertEqual(result.message.chat_id, message_data.chat_id)
        self.assertEqual(result.message.message_id, message_data.message_id)
        self.assertIsNotNone(result.message.author_id)
        self.assertEqual(result.attachments[0].id, attachment_data.id)
        self.assertEqual(result.attachments[0].message_id, attachment_data.message_id)
        self.assertEqual(result.attachments[0].chat_id, attachment_data.chat_id)

    def test_resolve_chat_config_existing(self):
        existing_config_data = ChatConfigSave(
            chat_id = "c1",
            language_iso_code = "en",
            language_name = "English",
            title = "Old Title",
            is_private = False,
            reply_chance_percent = 100,
        )
        existing_config_db = self.sql.chat_config_crud().save(existing_config_data)
        existing_config = ChatConfig.model_validate(existing_config_db)

        mapped_data = ChatConfigSave(
            chat_id = "c1",
            title = "New Title",
            is_private = True,
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

    def test_resolve_chat_config_new(self):
        mapped_data = ChatConfigSave(
            chat_id = "c1",
            title = "Title",
            is_private = True,
        )

        result = self.resolver.resolve_chat_config(mapped_data)
        saved_config_db = self.sql.chat_config_crud().get(mapped_data.chat_id)
        saved_config = ChatConfig.model_validate(saved_config_db)

        self.assertEqual(result, saved_config)
        self.assertEqual(result.chat_id, mapped_data.chat_id)
        self.assertEqual(result.language_iso_code, mapped_data.language_iso_code)
        self.assertEqual(result.language_name, mapped_data.language_name)
        self.assertEqual(result.title, mapped_data.title)
        self.assertEqual(result.is_private, mapped_data.is_private)
        self.assertEqual(result.reply_chance_percent, mapped_data.reply_chance_percent)

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
        saved_user_db = self.sql.user_crud().get_by_telegram_user_id(mapped_data.telegram_user_id)
        saved_user = User.model_validate(saved_user_db)

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
        saved_user_db = self.sql.user_crud().get(result.id)
        saved_user = User.model_validate(saved_user_db)

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

        self.assertEqual(str(context.exception), "User limit reached, try again later")
        mock_count.assert_called_once()

    def test_resolve_author_existing(self):
        existing_user_data = UserSave(
            telegram_user_id = 1,
            full_name = "Existing User",
            telegram_chat_id = "c1",
            open_ai_key = "sk-key",
            group = UserDB.Group.alpha,
        )
        existing_user_db = self.sql.user_crud().save(existing_user_data)
        existing_user = User.model_validate(existing_user_db)

        mapped_data = UserSave(
            telegram_user_id = 1,
            full_name = "Updated User",
            telegram_chat_id = "c2",
        )

        result = self.resolver.resolve_author(mapped_data)
        saved_user_db = self.sql.user_crud().get(result.id)
        saved_user = User.model_validate(saved_user_db)

        self.assertEqual(result, saved_user)
        self.assertEqual(result.id, existing_user.id)
        self.assertEqual(result.full_name, mapped_data.full_name)
        self.assertEqual(result.telegram_username, mapped_data.telegram_username)
        self.assertEqual(result.telegram_chat_id, mapped_data.telegram_chat_id)
        self.assertEqual(result.telegram_user_id, mapped_data.telegram_user_id)
        self.assertEqual(result.open_ai_key, existing_user.open_ai_key)
        self.assertEqual(result.group, existing_user.group)
        self.assertEqual(result.created_at, existing_user.created_at)

    @patch("db.crud.user.UserCRUD.get_by_telegram_user_id")
    @patch("db.crud.user.UserCRUD.get_by_telegram_username")
    def test_resolve_author_open_ai_key_reset(self, mock_get_by_username, mock_get_by_user_id):
        fake_user = User(
            id = UUID("123e4567-e89b-12d3-a456-426614174000"),
            full_name = "Existing User",
            telegram_username = "test_username",
            telegram_chat_id = "c1",
            telegram_user_id = 1,
            open_ai_key = None,
            group = UserDB.Group.alpha,
            created_at = datetime.now().date(),
        )

        mock_get_by_user_id.return_value = fake_user
        mock_get_by_username.return_value = None

        # test the no-key behavior
        mapped_data = UserSave(
            telegram_user_id = 1,
            full_name = "Test User",
            telegram_chat_id = "c1",
            open_ai_key = None,
        )
        result = self.resolver.resolve_author(mapped_data)
        self.assertIsNone(result.open_ai_key, "open_ai_key should be remain None when already None")

        # test the empty key behavior
        mapped_data.open_ai_key = ""
        fake_user.open_ai_key = ""
        result = self.resolver.resolve_author(mapped_data)
        self.assertIsNone(result.open_ai_key, "open_ai_key should be reset to None if empty")

        # test the whitespace behavior
        mapped_data.open_ai_key = "    "
        fake_user.open_ai_key = "    "
        result = self.resolver.resolve_author(mapped_data)
        self.assertIsNone(result.open_ai_key, "open_ai_key should be reset to None if whitespace")

        # test the valid key behavior
        mapped_data.open_ai_key = "valid_key"
        fake_user.open_ai_key = "valid_key"
        result = self.resolver.resolve_author(mapped_data)
        self.assertEqual(result.open_ai_key, "valid_key", "open_ai_key should remain unchanged if valid")

    def test_resolve_chat_message_new(self):
        mapped_data = ChatMessageSave(
            chat_id = "c1",
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
        old_message_data = ChatMessageSave(
            chat_id = "c1",
            message_id = "m1",
            author_id = None,
            sent_at = datetime.now() - timedelta(days = 1),
            text = "Old message",
        )
        self.sql.chat_message_crud().save(old_message_data)

        new_author_data = UserSave(full_name = "First Last", telegram_chat_id = "c1")
        new_author = User.model_validate(self.sql.user_crud().save(new_author_data))
        mapped_data = ChatMessageSave(
            chat_id = "c1",
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
        mapped_data = ChatMessageAttachmentSave(
            id = "i1",
            chat_id = "c1",
            message_id = "m1",
            last_url = "path/to/file.jpg",
            last_url_until = self.valid_url_timestamp(),
            extension = "jpg",
            mime_type = "image/jpeg",
        )

        result = self.resolver.resolve_chat_message_attachment(mapped_data)
        saved_attachment_db = self.sql.chat_message_attachment_crud().get(mapped_data.id)
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
        old_attachment_data = ChatMessageAttachmentSave(
            id = "i1",
            chat_id = "c1",
            message_id = "m1",
            size = 1,
            last_url = "path/to/file.jpg",
            last_url_until = self.valid_url_timestamp(),
            extension = "jpg",
            mime_type = "image/jpeg",
        )
        self.sql.chat_message_attachment_crud().save(old_attachment_data)

        mapped_data = ChatMessageAttachmentSave(id = "i1", chat_id = "c1", message_id = "m1")  # missing file data
        result = self.resolver.resolve_chat_message_attachment(mapped_data)  # injects file data from DB
        saved_attachment_db = self.sql.chat_message_attachment_crud().get(mapped_data.id)
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
