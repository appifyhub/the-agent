import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from uuid import UUID

import requests_mock

from db.model.user import UserDB
from db.schema.chat_config import ChatConfig
from db.schema.chat_message_attachment import ChatMessageAttachment
from db.schema.tools_cache import ToolsCache
from db.schema.user import User
from features.chat.attachments_describer import CACHE_TTL, AttachmentsDescriber
from util.config import config


class AttachmentsDescriberTest(unittest.TestCase):

    def setUp(self):
        config.web_retries = 1
        config.web_retry_delay_s = 0
        config.web_timeout_s = 1

        self.mock_di = MagicMock()
        self.mock_cache_crud = MagicMock()
        self.mock_user_crud = MagicMock()
        self.mock_chat_config_crud = MagicMock()
        self.mock_chat_message_attachment_crud = MagicMock()
        self.mock_access_token_resolver = MagicMock()
        self.mock_di.tools_cache_crud = self.mock_cache_crud
        self.mock_di.user_crud = self.mock_user_crud
        self.mock_di.chat_config_crud = self.mock_chat_config_crud
        self.mock_di.chat_message_attachment_crud = self.mock_chat_message_attachment_crud
        self.mock_di.access_token_resolver = self.mock_access_token_resolver
        self.mock_di.invoker_chat_id = "1"
        self.mock_di.invoker_chat.language_name = "Spanish"
        self.mock_di.invoker_chat.language_iso_code = "es"
        self.mock_di.telegram_bot_api = MagicMock()
        self.mock_di.tool_choice_resolver = MagicMock()
        self.mock_di.computer_vision_analyzer = MagicMock()

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
        m.get(str(self.attachment.last_url), content = b"image data", status_code = 200)
        self.mock_cache_crud.get.return_value = self.cache_entry.model_dump()

        mock_cv_instance = MagicMock()
        mock_cv_instance.execute.return_value = self.cached_content
        self.mock_di.computer_vision_analyzer.return_value = mock_cv_instance

        resolver = AttachmentsDescriber(
            additional_context = "context",
            attachment_ids = ["1"],
            di = self.mock_di,
        )
        result = resolver.execute()

        self.assertEqual(result, AttachmentsDescriber.Result.success)
        # Use the public get_result property if available, otherwise check the result length
        self.assertEqual(len(resolver.result), 1)
        self.assertEqual(resolver.result[0]["text_content"], self.cached_content)
        self.mock_di.computer_vision_analyzer.assert_not_called()
        mock_cv_instance.execute.assert_not_called()

    @requests_mock.Mocker()
    def test_execute_with_cache_miss(self, m: requests_mock.Mocker):
        m.get(str(self.attachment.last_url), content = b"image data", status_code = 200)
        self.mock_cache_crud.get.return_value = None

        mock_cv_instance = MagicMock()
        mock_cv_instance.execute.return_value = self.cached_content
        self.mock_di.computer_vision_analyzer.return_value = mock_cv_instance
        self.mock_di.tool_choice_resolver.require_tool.return_value = MagicMock()
        self.mock_access_token_resolver.require_access_token_for_tool.return_value = "**********"

        resolver = AttachmentsDescriber(
            additional_context = "context",
            attachment_ids = ["1"],
            di = self.mock_di,
        )
        result = resolver.execute()

        self.assertEqual(result, AttachmentsDescriber.Result.success)
        self.assertEqual(len(resolver.result), 1)
        self.assertEqual(resolver.result[0]["text_content"], self.cached_content)
        mock_cv_instance.execute.assert_called_once()
        self.mock_cache_crud.save.assert_called_once()

    def test_empty_attachment_ids_list(self):
        with self.assertRaises(ValueError) as context:
            AttachmentsDescriber(
                additional_context = "context",
                attachment_ids = [],
                di = self.mock_di,
            )
        self.assertIn("No attachment IDs provided", str(context.exception))

    def test_empty_attachment_id_string(self):
        with self.assertRaises(ValueError) as context:
            AttachmentsDescriber(
                additional_context = "context",
                attachment_ids = [""],
                di = self.mock_di,
            )
        self.assertIn("Attachment ID cannot be empty", str(context.exception))

    def test_attachment_not_found_in_db(self):
        self.mock_chat_message_attachment_crud.get.return_value = None

        with self.assertRaises(ValueError) as context:
            AttachmentsDescriber(
                additional_context = "context",
                attachment_ids = ["nonexistent"],
                di = self.mock_di,
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
        m.get(str(audio_attachment.last_url), content = b"audio data", status_code = 200)

        mock_audio_instance = MagicMock()
        mock_audio_instance.execute.return_value = "Audio transcription"
        self.mock_di.audio_transcriber.return_value = mock_audio_instance

        resolver = AttachmentsDescriber(
            additional_context = "context",
            attachment_ids = ["2"],
            di = self.mock_di,
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
        m.get(str(pdf_attachment.last_url), content = b"pdf data", status_code = 200)

        mock_document_instance = MagicMock()
        mock_document_instance.execute.return_value = "Document search results"
        self.mock_di.document_search.return_value = mock_document_instance

        resolver = AttachmentsDescriber(
            additional_context = "context",
            attachment_ids = ["4"],
            di = self.mock_di,
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
        m.get(str(unsupported_attachment.last_url), content = b"pdf data", status_code = 200)

        resolver = AttachmentsDescriber(
            additional_context = "context",
            attachment_ids = ["3"],
            di = self.mock_di,
        )
        content = resolver.fetch_text_content(unsupported_attachment)
        self.assertIsNone(content)
