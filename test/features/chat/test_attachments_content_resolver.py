import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID

import requests_mock

from db.model.user import UserDB
from db.schema.chat_config import ChatConfig
from db.schema.chat_message_attachment import ChatMessageAttachment
from db.schema.tools_cache import ToolsCache
from db.schema.user import User
from features.chat.attachments_content_resolver import AttachmentsContentResolver, CACHE_TTL
from util.config import config


class AttachmentsContentResolverTest(unittest.TestCase):

    def setUp(self):
        config.web_retries = 1
        config.web_retry_delay_s = 0
        config.web_timeout_s = 1

        self.mock_cache_crud = MagicMock()
        self.mock_user_crud = MagicMock()
        self.mock_chat_config_crud = MagicMock()
        self.mock_chat_message_crud = MagicMock()
        self.mock_chat_message_attachment_crud = MagicMock()
        self.mock_bot_api = MagicMock()

        self.cached_content = "resolved content"
        self.cache_entry = ToolsCache(
            key = "test_cache_key",
            value = self.cached_content,
            expires_at = datetime.now() + CACHE_TTL,
        )

        self.invoker_user = User(
            id = UUID(int = 1),
            group = UserDB.Group.beta,
            open_ai_key = "test_open_ai_key",
            created_at = datetime.now().date(),
        )
        self.chat_config = ChatConfig(
            chat_id = "1",
        )
        self.attachment = ChatMessageAttachment(
            id = "1",
            chat_id = "1",
            message_id = "1",
            mime_type = "image/png",
            last_url = "http://test.com/image.png",
            last_url_until = int((datetime.now() + timedelta(days = 1)).timestamp()),
        )

        self.mock_user_crud.get.return_value = self.invoker_user.model_dump()
        self.mock_chat_config_crud.get.return_value = self.chat_config.model_dump()
        self.mock_chat_message_attachment_crud.get.return_value = self.attachment.model_dump()
        self.mock_chat_message_attachment_crud.save.return_value = self.attachment.model_dump()
        self.mock_cache_crud.create_key.return_value = "test_cache_key"

    @requests_mock.Mocker()
    def test_execute_with_cache_hit(self, m: requests_mock.Mocker):
        m.get(self.attachment.last_url, content = b"image data", status_code = 200)
        self.mock_cache_crud.get.return_value = self.cache_entry.model_dump()

        resolver = AttachmentsContentResolver(
            chat_id = "1",
            invoker_user_id_hex = "00000000-0000-0000-0000-000000000001",
            additional_context = "context",
            attachment_ids = ["1"],
            bot_api = self.mock_bot_api,
            user_dao = self.mock_user_crud,
            chat_config_dao = self.mock_chat_config_crud,
            chat_message_dao = self.mock_chat_message_crud,
            chat_message_attachment_dao = self.mock_chat_message_attachment_crud,
            cache_dao = self.mock_cache_crud,
        )
        result = resolver.execute()
        self.assertEqual(result, AttachmentsContentResolver.Result.success)
        self.assertEqual(resolver.contents, [self.cached_content])

    @requests_mock.Mocker()
    def test_execute_with_cache_miss(self, m: requests_mock.Mocker):
        m.get(self.attachment.last_url, content = b"image data", status_code = 200)
        self.mock_cache_crud.get.return_value = None

        with patch("features.chat.attachments_content_resolver.ComputerVisionAnalyzer") as mock_cv_analyzer:
            # Set up the mock for ComputerVisionAnalyzer
            mock_cv_instance = MagicMock()
            mock_cv_instance.execute.return_value = self.cached_content
            mock_cv_analyzer.return_value = mock_cv_instance

            resolver = AttachmentsContentResolver(
                chat_id = "1",
                invoker_user_id_hex = "00000000-0000-0000-0000-000000000001",
                additional_context = "context",
                attachment_ids = ["1"],
                bot_api = self.mock_bot_api,
                user_dao = self.mock_user_crud,
                chat_config_dao = self.mock_chat_config_crud,
                chat_message_dao = self.mock_chat_message_crud,
                chat_message_attachment_dao = self.mock_chat_message_attachment_crud,
                cache_dao = self.mock_cache_crud,
            )
            result = resolver.execute()

            self.assertEqual(result, AttachmentsContentResolver.Result.success)
            self.assertEqual(resolver.contents, [self.cached_content])
            mock_cv_instance.execute.assert_called_once()
            self.mock_cache_crud.save.assert_called_once()

    def test_missing_invoker_user(self):
        self.mock_user_crud.get.return_value = None

        with self.assertRaises(ValueError):
            AttachmentsContentResolver(
                chat_id = "1",
                invoker_user_id_hex = "00000000-0000-0000-0000-000000000001",
                additional_context = "context",
                attachment_ids = ["1"],
                bot_api = self.mock_bot_api,
                user_dao = self.mock_user_crud,
                chat_config_dao = self.mock_chat_config_crud,
                chat_message_dao = self.mock_chat_message_crud,
                chat_message_attachment_dao = self.mock_chat_message_attachment_crud,
                cache_dao = self.mock_cache_crud,
            )

    def test_insufficient_user_perms(self):
        self.invoker_user.group = UserDB.Group.standard
        self.mock_user_crud.get.return_value = self.invoker_user.model_dump()

        with self.assertRaises(ValueError) as context:
            AttachmentsContentResolver(
                chat_id = "1",
                invoker_user_id_hex = "00000000-0000-0000-0000-000000000001",
                additional_context = "context",
                attachment_ids = ["1"],
                bot_api = self.mock_bot_api,
                user_dao = self.mock_user_crud,
                chat_config_dao = self.mock_chat_config_crud,
                chat_message_dao = self.mock_chat_message_crud,
                chat_message_attachment_dao = self.mock_chat_message_attachment_crud,
                cache_dao = self.mock_cache_crud,
            )
        self.assertTrue("not allowed to resolve attachments" in str(context.exception))

    def test_missing_chat_config(self):
        self.mock_chat_config_crud.get.return_value = None

        with self.assertRaises(ValueError):
            AttachmentsContentResolver(
                chat_id = "1",
                invoker_user_id_hex = "00000000-0000-0000-0000-000000000001",
                additional_context = "context",
                attachment_ids = ["1"],
                bot_api = self.mock_bot_api,
                user_dao = self.mock_user_crud,
                chat_config_dao = self.mock_chat_config_crud,
                chat_message_dao = self.mock_chat_message_crud,
                chat_message_attachment_dao = self.mock_chat_message_attachment_crud,
                cache_dao = self.mock_cache_crud,
            )

    def test_fetch_text_content_with_invalid_mime_type(self):
        self.attachment.mime_type = "application/pdf"
        self.mock_chat_message_attachment_crud.get.return_value = self.attachment.model_dump()

        resolver = AttachmentsContentResolver(
            chat_id = "1",
            invoker_user_id_hex = "00000000-0000-0000-0000-000000000001",
            additional_context = "context",
            attachment_ids = ["1"],
            bot_api = self.mock_bot_api,
            user_dao = self.mock_user_crud,
            chat_config_dao = self.mock_chat_config_crud,
            chat_message_dao = self.mock_chat_message_crud,
            chat_message_attachment_dao = self.mock_chat_message_attachment_crud,
            cache_dao = self.mock_cache_crud,
        )
        content = resolver.fetch_text_content(self.attachment)
        self.assertIsNone(content)

    @requests_mock.Mocker()
    def test_fetch_text_content_with_failed_image_retrieval(self, m: requests_mock.Mocker):
        m.get(self.attachment.last_url, status_code = 404)

        resolver = AttachmentsContentResolver(
            chat_id = "1",
            invoker_user_id_hex = "00000000-0000-0000-0000-000000000001",
            additional_context = "context",
            attachment_ids = ["1"],
            bot_api = self.mock_bot_api,
            user_dao = self.mock_user_crud,
            chat_config_dao = self.mock_chat_config_crud,
            chat_message_dao = self.mock_chat_message_crud,
            chat_message_attachment_dao = self.mock_chat_message_attachment_crud,
            cache_dao = self.mock_cache_crud,
        )
        content = resolver.fetch_text_content(self.attachment)
        self.assertIsNone(content)
