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
from features.chat.attachments_content_resolver import CACHE_TTL, AttachmentsContentResolver
from features.chat.telegram.sdk.telegram_bot_api import TelegramBotAPI
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
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
        self.mock_sponsorship_dao = MagicMock()
        self.mock_bot_sdk = MagicMock(spec = TelegramBotSDK)
        self.mock_bot_sdk.api = MagicMock(spec = TelegramBotAPI)

        self.cached_content = "resolved content"
        self.cache_entry = ToolsCache(
            key = "test_cache_key",
            value = self.cached_content,
            expires_at = datetime.now() + CACHE_TTL,
        )

        self.invoker_user = User(
            id = UUID(int = 1),
            full_name = "Test User",
            telegram_username = "test_user",
            telegram_chat_id = "test_chat_id",
            telegram_user_id = 1,
            open_ai_key = "test_openai_key",
            anthropic_key = "test_anthropic_key",
            perplexity_key = "test_perplexity_key",
            replicate_key = "test_replicate_key",
            rapid_api_key = "test_rapid_api_key",
            coinmarketcap_key = "test_coinmarketcap_key",
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.chat_config = ChatConfig(
            chat_id = "1",
            language_name = "Spanish",
            language_iso_code = "es",
        )
        self.attachment = ChatMessageAttachment(
            id = "1",
            chat_id = "1",
            message_id = "1",
            mime_type = "image/png",
            extension = "png",
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

        with patch("features.chat.attachments_content_resolver.ComputerVisionAnalyzer") as mock_cv_analyzer:
            mock_cv_instance = MagicMock()
            mock_cv_instance.execute.return_value = self.cached_content
            mock_cv_analyzer.return_value = mock_cv_instance

            resolver = AttachmentsContentResolver(
                chat_id = "1",
                invoker_user_id_hex = "00000000-0000-0000-0000-000000000001",
                additional_context = "context",
                attachment_ids = ["1"],
                bot_sdk = self.mock_bot_sdk,
                user_dao = self.mock_user_crud,
                chat_config_dao = self.mock_chat_config_crud,
                chat_message_dao = self.mock_chat_message_crud,
                chat_message_attachment_dao = self.mock_chat_message_attachment_crud,
                cache_dao = self.mock_cache_crud,
                sponsorship_dao = self.mock_sponsorship_dao,
            )
            result = resolver.execute()

            self.assertEqual(result, AttachmentsContentResolver.Result.success)
            self.assertEqual(resolver.contents, [self.cached_content])
            mock_cv_analyzer.assert_not_called()
            mock_cv_instance.execute.assert_not_called()

    @requests_mock.Mocker()
    def test_execute_with_cache_miss(self, m: requests_mock.Mocker):
        m.get(self.attachment.last_url, content = b"image data", status_code = 200)
        self.mock_cache_crud.get.return_value = None

        with patch("features.chat.attachments_content_resolver.ComputerVisionAnalyzer") as mock_cv_analyzer:
            mock_cv_instance = MagicMock()
            mock_cv_instance.execute.return_value = self.cached_content
            mock_cv_analyzer.return_value = mock_cv_instance

            with patch("features.chat.attachments_content_resolver.AccessTokenResolver") as mock_token_resolver_class:
                # Mock the AccessTokenResolver to return user tokens directly
                mock_token_resolver = MagicMock()
                mock_token_resolver.require_access_token_for_tool.return_value = "**********"
                mock_token_resolver_class.return_value = mock_token_resolver

                resolver = AttachmentsContentResolver(
                    chat_id = "1",
                    invoker_user_id_hex = "00000000-0000-0000-0000-000000000001",
                    additional_context = "context",
                    attachment_ids = ["1"],
                    bot_sdk = self.mock_bot_sdk,
                    user_dao = self.mock_user_crud,
                    chat_config_dao = self.mock_chat_config_crud,
                    chat_message_dao = self.mock_chat_message_crud,
                    chat_message_attachment_dao = self.mock_chat_message_attachment_crud,
                    cache_dao = self.mock_cache_crud,
                    sponsorship_dao = self.mock_sponsorship_dao,
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
                bot_sdk = self.mock_bot_sdk,
                user_dao = self.mock_user_crud,
                chat_config_dao = self.mock_chat_config_crud,
                chat_message_dao = self.mock_chat_message_crud,
                chat_message_attachment_dao = self.mock_chat_message_attachment_crud,
                cache_dao = self.mock_cache_crud,
                sponsorship_dao = self.mock_sponsorship_dao,
            )

    def test_missing_chat_config(self):
        self.mock_chat_config_crud.get.return_value = None

        with self.assertRaises(ValueError):
            AttachmentsContentResolver(
                chat_id = "1",
                invoker_user_id_hex = "00000000-0000-0000-0000-000000000001",
                additional_context = "context",
                attachment_ids = ["1"],
                bot_sdk = self.mock_bot_sdk,
                user_dao = self.mock_user_crud,
                chat_config_dao = self.mock_chat_config_crud,
                chat_message_dao = self.mock_chat_message_crud,
                chat_message_attachment_dao = self.mock_chat_message_attachment_crud,
                cache_dao = self.mock_cache_crud,
                sponsorship_dao = self.mock_sponsorship_dao,
            )

    def test_empty_attachment_ids_list(self):
        with self.assertRaises(ValueError) as context:
            AttachmentsContentResolver(
                chat_id = "1",
                invoker_user_id_hex = "00000000-0000-0000-0000-000000000001",
                additional_context = "context",
                attachment_ids = [],
                bot_sdk = self.mock_bot_sdk,
                user_dao = self.mock_user_crud,
                chat_config_dao = self.mock_chat_config_crud,
                chat_message_dao = self.mock_chat_message_crud,
                chat_message_attachment_dao = self.mock_chat_message_attachment_crud,
                cache_dao = self.mock_cache_crud,
                sponsorship_dao = self.mock_sponsorship_dao,
            )
        self.assertIn("No attachment IDs provided", str(context.exception))

    def test_empty_attachment_id_string(self):
        with self.assertRaises(ValueError) as context:
            AttachmentsContentResolver(
                chat_id = "1",
                invoker_user_id_hex = "00000000-0000-0000-0000-000000000001",
                additional_context = "context",
                attachment_ids = [""],
                bot_sdk = self.mock_bot_sdk,
                user_dao = self.mock_user_crud,
                chat_config_dao = self.mock_chat_config_crud,
                chat_message_dao = self.mock_chat_message_crud,
                chat_message_attachment_dao = self.mock_chat_message_attachment_crud,
                cache_dao = self.mock_cache_crud,
                sponsorship_dao = self.mock_sponsorship_dao,
            )
        self.assertIn("Attachment ID cannot be empty", str(context.exception))

    def test_attachment_not_found_in_db(self):
        self.mock_chat_message_attachment_crud.get.return_value = None

        with self.assertRaises(ValueError) as context:
            AttachmentsContentResolver(
                chat_id = "1",
                invoker_user_id_hex = "00000000-0000-0000-0000-000000000001",
                additional_context = "context",
                attachment_ids = ["nonexistent"],
                bot_sdk = self.mock_bot_sdk,
                user_dao = self.mock_user_crud,
                chat_config_dao = self.mock_chat_config_crud,
                chat_message_dao = self.mock_chat_message_crud,
                chat_message_attachment_dao = self.mock_chat_message_attachment_crud,
                cache_dao = self.mock_cache_crud,
                sponsorship_dao = self.mock_sponsorship_dao,
            )
        self.assertIn("not found in DB", str(context.exception))

    @requests_mock.Mocker()
    def test_fetch_text_content_with_audio(self, m: requests_mock.Mocker):
        audio_attachment = ChatMessageAttachment(
            id = "2",
            chat_id = "1",
            message_id = "2",
            mime_type = "audio/mpeg",
            extension = "mp3",
            last_url = "http://test.com/audio.mp3",
            last_url_until = int((datetime.now() + timedelta(days = 1)).timestamp()),
        )
        m.get(audio_attachment.last_url, content = b"audio data", status_code = 200)

        with patch("features.chat.attachments_content_resolver.AudioTranscriber") as mock_audio_transcriber:
            mock_audio_instance = MagicMock()
            mock_audio_instance.execute.return_value = "Audio transcription"
            mock_audio_transcriber.return_value = mock_audio_instance

            with patch("features.chat.attachments_content_resolver.AccessTokenResolver") as mock_token_resolver_class:
                # Mock the AccessTokenResolver to return user tokens directly
                mock_token_resolver = MagicMock()
                mock_token_resolver.require_access_token_for_tool.return_value = "**********"
                mock_token_resolver_class.return_value = mock_token_resolver

                resolver = AttachmentsContentResolver(
                    chat_id = "1",
                    invoker_user_id_hex = "00000000-0000-0000-0000-000000000001",
                    additional_context = "context",
                    attachment_ids = ["2"],
                    bot_sdk = self.mock_bot_sdk,
                    user_dao = self.mock_user_crud,
                    chat_config_dao = self.mock_chat_config_crud,
                    chat_message_dao = self.mock_chat_message_crud,
                    chat_message_attachment_dao = self.mock_chat_message_attachment_crud,
                    cache_dao = self.mock_cache_crud,
                    sponsorship_dao = self.mock_sponsorship_dao,
                )
                content = resolver.fetch_text_content(audio_attachment)

                self.assertEqual(content, "Audio transcription")
                mock_audio_instance.execute.assert_called_once()

    @requests_mock.Mocker()
    def test_fetch_text_content_with_pdf_document(self, m: requests_mock.Mocker):
        pdf_attachment = ChatMessageAttachment(
            id = "4",
            chat_id = "1",
            message_id = "4",
            mime_type = "application/pdf",
            extension = "pdf",
            last_url = "http://test.com/document.pdf",
            last_url_until = int((datetime.now() + timedelta(days = 1)).timestamp()),
        )
        m.get(pdf_attachment.last_url, content = b"pdf data", status_code = 200)

        with patch("features.chat.attachments_content_resolver.DocumentSearch") as mock_document_search:
            mock_document_instance = MagicMock()
            mock_document_instance.execute.return_value = "Document search results"
            mock_document_search.return_value = mock_document_instance

            with patch("features.chat.attachments_content_resolver.AccessTokenResolver") as mock_token_resolver_class:
                # Mock the AccessTokenResolver to return user tokens directly
                mock_token_resolver = MagicMock()
                mock_token_resolver.require_access_token_for_tool.return_value = "**********"
                mock_token_resolver_class.return_value = mock_token_resolver

                resolver = AttachmentsContentResolver(
                    chat_id = "1",
                    invoker_user_id_hex = "00000000-0000-0000-0000-000000000001",
                    additional_context = "context",
                    attachment_ids = ["4"],
                    bot_sdk = self.mock_bot_sdk,
                    user_dao = self.mock_user_crud,
                    chat_config_dao = self.mock_chat_config_crud,
                    chat_message_dao = self.mock_chat_message_crud,
                    chat_message_attachment_dao = self.mock_chat_message_attachment_crud,
                    cache_dao = self.mock_cache_crud,
                    sponsorship_dao = self.mock_sponsorship_dao,
                )
                content = resolver.fetch_text_content(pdf_attachment)

                self.assertEqual(content, "Document search results")
                mock_document_instance.execute.assert_called_once()

    @requests_mock.Mocker()
    def test_fetch_text_content_with_unsupported_type(self, m: requests_mock.Mocker):
        unsupported_attachment = ChatMessageAttachment(
            id = "3",
            chat_id = "1",
            message_id = "3",
            mime_type = "application/xxx",
            extension = "xxx",
            last_url = "http://test.com/document.xxx",
            last_url_until = int((datetime.now() + timedelta(days = 1)).timestamp()),
        )
        m.get(unsupported_attachment.last_url, content = b"pdf data", status_code = 200)

        resolver = AttachmentsContentResolver(
            chat_id = "1",
            invoker_user_id_hex = "00000000-0000-0000-0000-000000000001",
            additional_context = "context",
            attachment_ids = ["3"],
            bot_sdk = self.mock_bot_sdk,
            user_dao = self.mock_user_crud,
            chat_config_dao = self.mock_chat_config_crud,
            chat_message_dao = self.mock_chat_message_crud,
            chat_message_attachment_dao = self.mock_chat_message_attachment_crud,
            cache_dao = self.mock_cache_crud,
            sponsorship_dao = self.mock_sponsorship_dao,
        )
        content = resolver.fetch_text_content(unsupported_attachment)
        self.assertIsNone(content)
