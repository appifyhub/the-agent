import unittest
from unittest.mock import Mock, patch

from db.schema.chat_message import ChatMessage
from db.schema.chat_message_attachment import ChatMessageAttachment
from di.di import DI
from features.chat.telegram.sdk.telegram_bot_api import TelegramBotAPI
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.chat.telegram.telegram_data_resolver import TelegramDataResolver
from features.chat.telegram.telegram_domain_mapper import TelegramDomainMapper
from util.errors import InternalError


class TelegramBotSDKTest(unittest.TestCase):

    sdk: TelegramBotSDK
    mock_di: DI

    def setUp(self):
        # Create mock DI with all required dependencies
        self.mock_di = Mock(spec = DI)

        # noinspection PyPropertyAccess
        self.mock_di.telegram_bot_api = Mock(spec = TelegramBotAPI)
        # noinspection PyPropertyAccess
        self.mock_di.telegram_data_resolver = Mock(spec = TelegramDataResolver)
        # noinspection PyPropertyAccess
        self.mock_di.telegram_domain_mapper = Mock(spec = TelegramDomainMapper)

        self.sdk = TelegramBotSDK(self.mock_di)

        self.user_id = "001"
        self.chat_id = "123"
        self.message_id = "456"
        self.api_response = {
            "result": {
                "message_id": self.message_id,
                "chat": {
                    "id": self.chat_id,
                    "type": "private",  # Required field
                },
                "date": 1234567890,  # Required field
                "text": "test message",
            },
        }
        self.mock_di.telegram_bot_api.send_text_message.return_value = self.api_response
        self.mock_di.telegram_bot_api.send_photo.return_value = self.api_response
        self.mock_di.telegram_bot_api.send_document.return_value = self.api_response
        self.mock_di.telegram_bot_api.send_button_link.return_value = self.api_response
        self.mock_di.telegram_bot_api.get_chat_member.return_value = self.api_response

    @patch.object(TelegramDomainMapper, "map_update")
    def test_send_text_message(self, mock_map_update):
        text = "test message"
        expected_message = Mock(spec = ChatMessage)
        mock_map_update.return_value = Mock(spec = TelegramDomainMapper.Result)
        self.mock_di.telegram_data_resolver.resolve.return_value = Mock(
            spec = TelegramDataResolver.Result,
            message = expected_message,
            attachments = [Mock(spec = ChatMessageAttachment)],
        )

        result = self.sdk.send_text_message(chat_id = self.chat_id, text = text)

        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_api.send_text_message.assert_called_once_with(
            chat_id = self.chat_id,
            text = text,
            parse_mode = "markdown",
            disable_notification = False,
            link_preview_options = None,
        )
        self.assertEqual(result, expected_message)

    @patch.object(TelegramDomainMapper, "map_update")
    def test_send_photo(self, mock_map_update):
        photo_url = "http://test.com/photo.jpg"
        caption = "test photo"
        expected_message = Mock(spec = ChatMessage)
        mock_map_update.return_value = Mock(spec = TelegramDomainMapper.Result)
        self.mock_di.telegram_data_resolver.resolve.return_value = Mock(
            spec = TelegramDataResolver.Result,
            message = expected_message,
            attachments = [Mock(spec = ChatMessageAttachment)],
        )

        result = self.sdk.send_photo(
            chat_id = self.chat_id,
            photo_url = photo_url,
            caption = caption,
        )

        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_api.send_photo.assert_called_once_with(
            chat_id = self.chat_id,
            photo_url = photo_url,
            caption = caption,
            parse_mode = "markdown",
            disable_notification = False,
        )
        self.assertEqual(result, expected_message)

    @patch.object(TelegramDomainMapper, "map_update")
    def test_send_document(self, mock_map_update):
        doc_url = "http://test.com/doc.pdf"
        caption = "test document"
        expected_message = Mock(spec = ChatMessage)
        mock_map_update.return_value = Mock(spec = TelegramDomainMapper.Result)
        self.mock_di.telegram_data_resolver.resolve.return_value = Mock(
            spec = TelegramDataResolver.Result,
            message = expected_message,
            attachments = [Mock(spec = ChatMessageAttachment)],  # Add at least one attachment
        )

        result = self.sdk.send_document(
            chat_id = self.chat_id,
            document_url = doc_url,
            caption = caption,
        )

        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_api.send_document.assert_called_once_with(
            chat_id = self.chat_id,
            document_url = doc_url,
            caption = caption,
            parse_mode = "markdown",
            thumbnail = None,
            disable_notification = False,
        )
        self.assertEqual(result, expected_message)

    def test_set_status_typing(self):
        self.sdk.set_status_typing(self.chat_id)
        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_api.set_status_typing.assert_called_once_with(self.chat_id)

    def test_set_status_uploading_image(self):
        self.sdk.set_status_uploading_image(self.chat_id)
        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_api.set_status_uploading_image.assert_called_once_with(self.chat_id)

    def test_set_reaction(self):
        reaction = "👍"
        self.sdk.set_reaction(self.chat_id, self.message_id, reaction)
        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_api.set_reaction.assert_called_once_with(
            chat_id = self.chat_id,
            message_id = self.message_id,
            reaction = reaction,
        )

    @patch.object(TelegramDomainMapper, "map_update")
    def test_send_button_link(self, mock_map_update):
        link_url = "https://test.com"
        expected_message = Mock(spec = ChatMessage)
        mock_map_update.return_value = Mock(spec = TelegramDomainMapper.Result)
        self.mock_di.telegram_data_resolver.resolve.return_value = Mock(
            spec = TelegramDataResolver.Result,
            message = expected_message,
            attachments = [Mock(spec = ChatMessageAttachment)],
        )

        # Test settings button
        result = self.sdk.send_button_link(
            chat_id = self.chat_id,
            link_url = link_url,
            button_text = "⚙️",
        )

        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_api.send_button_link.assert_called_with(self.chat_id, link_url, "⚙️")
        self.assertEqual(result, expected_message)

        # Test default-to-settings button
        result = self.sdk.send_button_link(
            chat_id = self.chat_id,
            link_url = link_url,
        )

        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_api.send_button_link.assert_called_with(self.chat_id, link_url, "⚙️")
        self.assertEqual(result, expected_message)

        # Test custom button text
        result = self.sdk.send_button_link(
            chat_id = self.chat_id,
            link_url = link_url,
            button_text = "test",
        )

        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_api.send_button_link.assert_called_with(self.chat_id, link_url, "test")
        self.assertEqual(result, expected_message)

    def test_get_chat_member(self):
        self.sdk.get_chat_member(self.chat_id, self.user_id)
        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_api.get_chat_member.assert_called_once_with(self.chat_id, self.user_id)

    def test_store_api_response_mapping_failure(self):
        self.mock_di.telegram_domain_mapper.map_update.return_value = None

        with self.assertRaises(InternalError) as context:
            # noinspection PyUnresolvedReferences
            self.sdk._TelegramBotSDK__store_api_response_as_message(self.api_response)
        self.assertTrue("domain mapping failed" in str(context.exception))

    @patch.object(TelegramDomainMapper, "map_update")
    def test_store_api_response_resolution_failure(self, mock_map_update):
        mock_map_update.return_value = Mock(spec = TelegramDomainMapper.Result)
        self.mock_di.telegram_data_resolver.resolve.return_value = Mock(
            spec = TelegramDataResolver.Result,
            message = None,
            attachments = None,
        )

        with self.assertRaises(InternalError) as context:
            # noinspection PyUnresolvedReferences
            self.sdk._TelegramBotSDK__store_api_response_as_message(self.api_response)
        self.assertTrue("data resolution failed" in str(context.exception))
