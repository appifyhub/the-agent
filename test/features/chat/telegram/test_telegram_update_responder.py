import unittest
from unittest.mock import Mock, patch
from uuid import UUID

from db.sql_util import SQLUtil
from langchain_core.messages import AIMessage
from pydantic import SecretStr

from api.settings_controller import SettingsController
from db.crud.chat_config import ChatConfigCRUD
from db.crud.chat_message import ChatMessageCRUD
from db.crud.chat_message_attachment import ChatMessageAttachmentCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.model.chat_config import ChatConfigDB
from db.model.user import UserDB
from db.schema.chat_config import ChatConfig
from db.schema.chat_message import ChatMessage
from db.schema.user import User
from features.chat.telegram.domain_langchain_mapper import DomainLangchainMapper
from features.chat.telegram.model.update import Update
from features.chat.telegram.sdk.telegram_bot_api import TelegramBotAPI
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.chat.telegram.telegram_data_resolver import TelegramDataResolver
from features.chat.telegram.telegram_domain_mapper import TelegramDomainMapper
from features.chat.telegram.telegram_update_responder import respond_to_update
from features.external_tools.access_token_resolver import AccessTokenResolver
from features.sponsorships.sponsorship_service import SponsorshipService


class TelegramUpdateResponderTest(unittest.TestCase):
    sql: SQLUtil
    update: Update
    telegram_bot_sdk: TelegramBotSDK
    telegram_domain_mapper: TelegramDomainMapper
    telegram_data_resolver: TelegramDataResolver
    domain_langchain_mapper: DomainLangchainMapper
    user_dao: UserCRUD
    sponsorship_dao: SponsorshipCRUD
    chat_messages_dao: ChatMessageCRUD
    chat_message_attachment_dao: ChatMessageAttachmentCRUD
    chat_config_dao: ChatConfigCRUD
    sponsorship_service: SponsorshipService
    settings_controller: SettingsController
    access_token_resolver: AccessTokenResolver

    def setUp(self):
        # create all the mocks
        self.sql = SQLUtil()
        self.update = Mock(spec = Update)
        self.telegram_bot_sdk = Mock(spec = TelegramBotSDK)
        self.telegram_bot_sdk.api = Mock(spec = TelegramBotAPI)
        self.telegram_domain_mapper = Mock(spec = TelegramDomainMapper)
        self.telegram_data_resolver = Mock(spec = TelegramDataResolver)
        self.domain_langchain_mapper = Mock(spec = DomainLangchainMapper)
        self.user_dao = Mock(spec = UserCRUD)
        self.sponsorship_dao = Mock(spec = SponsorshipCRUD)
        self.chat_messages_dao = Mock(spec = ChatMessageCRUD)
        self.chat_message_attachment_dao = Mock(spec = ChatMessageAttachmentCRUD)
        self.chat_config_dao = Mock(spec = ChatConfigCRUD)
        self.sponsorship_service = Mock(spec = SponsorshipService)
        self.settings_controller = Mock(spec = SettingsController)
        self.access_token_resolver = Mock(spec = AccessTokenResolver)

        self.access_token_resolver.get_access_token_for_tool.return_value = SecretStr("test_token")
        # patch all dependencies in the correct namespace where they are used in telegram_update_responder
        patcher_get_detached_session = patch("features.chat.telegram.telegram_update_responder.get_detached_session")
        self.addCleanup(patcher_get_detached_session.stop)
        self.mock_get_detached_session = patcher_get_detached_session.start()
        self.mock_get_detached_session.return_value.__enter__.return_value = self.sql.start_session()
        patcher_telegram_bot_sdk = patch(
            "features.chat.telegram.telegram_update_responder.TelegramBotSDK",
            return_value = self.telegram_bot_sdk,
        )
        patcher_telegram_domain_mapper = patch(
            "features.chat.telegram.telegram_update_responder.TelegramDomainMapper",
            return_value = self.telegram_domain_mapper,
        )
        patcher_domain_langchain_mapper = patch(
            "features.chat.telegram.telegram_update_responder.DomainLangchainMapper",
            return_value = self.domain_langchain_mapper,
        )
        patcher_telegram_data_resolver = patch(
            "features.chat.telegram.telegram_update_responder.TelegramDataResolver",
            return_value = self.telegram_data_resolver,
        )
        patcher_user_crud = patch(
            "features.chat.telegram.telegram_update_responder.UserCRUD",
            return_value = self.user_dao,
        )
        patcher_sponsorship_crud = patch(
            "features.chat.telegram.telegram_update_responder.SponsorshipCRUD",
            return_value = self.sponsorship_dao,
        )
        patcher_chat_message_crud = patch(
            "features.chat.telegram.telegram_update_responder.ChatMessageCRUD",
            return_value = self.chat_messages_dao,
        )
        patcher_chat_message_attachment_crud = patch(
            "features.chat.telegram.telegram_update_responder.ChatMessageAttachmentCRUD",
            return_value = self.chat_message_attachment_dao,
        )
        patcher_chat_config_crud = patch(
            "features.chat.telegram.telegram_update_responder.ChatConfigCRUD",
            return_value = self.chat_config_dao,
        )
        patcher_sponsorship_service = patch(
            "features.chat.telegram.telegram_update_responder.SponsorshipService",
            return_value = self.sponsorship_service,
        )
        patcher_settings_controller = patch(
            "features.chat.telegram.telegram_update_responder.SettingsController",
            return_value = self.settings_controller,
        )
        patcher_access_token_resolver = patch(
            "features.chat.telegram.telegram_update_responder.AccessTokenResolver",
            return_value = self.access_token_resolver,
        )

        # start the patchers
        patcher_telegram_bot_sdk.start()
        patcher_telegram_domain_mapper.start()
        patcher_domain_langchain_mapper.start()
        patcher_telegram_data_resolver.start()
        patcher_user_crud.start()
        patcher_sponsorship_crud.start()
        patcher_chat_message_crud.start()
        patcher_chat_message_attachment_crud.start()
        patcher_chat_config_crud.start()
        patcher_sponsorship_service.start()
        patcher_settings_controller.start()
        patcher_access_token_resolver.start()

        # make sure to stop the patchers after the test
        self.addCleanup(patcher_telegram_bot_sdk.stop)
        self.addCleanup(patcher_telegram_domain_mapper.stop)
        self.addCleanup(patcher_domain_langchain_mapper.stop)
        self.addCleanup(patcher_telegram_data_resolver.stop)
        self.addCleanup(patcher_user_crud.stop)
        self.addCleanup(patcher_sponsorship_crud.stop)
        self.addCleanup(patcher_chat_message_crud.stop)
        self.addCleanup(patcher_chat_message_attachment_crud.stop)
        self.addCleanup(patcher_chat_config_crud.stop)
        self.addCleanup(patcher_sponsorship_service.stop)
        self.addCleanup(patcher_settings_controller.stop)
        self.addCleanup(patcher_access_token_resolver.stop)

    def tearDown(self):
        self.sql.end_session()

    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.execute")
    def test_successful_response(self, mock_execute):
        mock_execute.return_value = Mock(spec = AIMessage, content = "Test response")

        self.telegram_domain_mapper.map_update.return_value = Mock(
            spec = TelegramDomainMapper.Result,
            message = Mock(spec = ChatMessage, message_id = "test-message-id", text = "Test message text"),
        )
        self.telegram_data_resolver.resolve.return_value = Mock(
            spec = TelegramDataResolver.Result,
            chat = Mock(
                spec = ChatConfig,
                chat_id = "123",
                language_name = "English",
                language_iso_code = "en",
                title = "Test Chat",
                is_private = False,
                reply_chance_percent = 100,
                release_notifications = ChatConfigDB.ReleaseNotifications.all,
            ),
            author = Mock(
                spec = User,
                id = UUID(int = 1),
                telegram_username = "test_user",
                full_name = "Test User",
                telegram_user_id = 1,
                group = UserDB.Group.standard,
            ),
        )
        self.chat_messages_dao.get_latest_chat_messages.return_value = []
        self.user_dao.get.return_value = None

        self.domain_langchain_mapper.map_bot_message_to_storage.return_value = [
            Mock(chat_id = "123", text = "Test response"),
        ]

        result = respond_to_update(self.update)

        self.assertTrue(result)
        # noinspection PyUnresolvedReferences
        self.user_dao.save.assert_called_once()
        mock_execute.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.telegram_bot_sdk.send_text_message.assert_called_once_with("123", "Test response")

    def test_empty_response(self):
        self.telegram_domain_mapper.map_update.return_value = Mock(spec = TelegramDomainMapper.Result)
        self.telegram_data_resolver.resolve.return_value = Mock(
            spec = TelegramDataResolver.Result,
            chat = Mock(spec = ChatConfig, chat_id = "123"),
            author = Mock(spec = User, id = UUID(int = 1)),
        )
        self.chat_messages_dao.get_latest_chat_messages.return_value = []

        with patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot") as MockTelegramChatBot:
            mock_bot = MockTelegramChatBot.return_value
            mock_bot.execute.return_value = Mock(content = "")

            result = respond_to_update(self.update)

        self.assertFalse(result)
        # noinspection PyUnresolvedReferences
        self.telegram_bot_sdk.send_text_message.assert_not_called()
        # noinspection PyUnresolvedReferences
        self.chat_messages_dao.save.assert_not_called()

    def test_mapping_error(self):
        self.telegram_domain_mapper.map_update.return_value = None

        with patch("features.prompting.prompt_library.error_general_problem", return_value = "Mapping error"):
            self.domain_langchain_mapper.map_bot_message_to_storage.return_value = [
                Mock(chat_id = "123", text = "Mapping error"),
            ]
            result = respond_to_update(self.update)

        self.assertFalse(result)

        # noinspection PyUnresolvedReferences
        self.domain_langchain_mapper.map_bot_message_to_storage.assert_not_called()
        # noinspection PyUnresolvedReferences
        self.telegram_bot_sdk.send_text_message.assert_not_called()
        # noinspection PyUnresolvedReferences
        self.chat_messages_dao.save.assert_not_called()

    def test_general_exception(self):
        self.telegram_domain_mapper.map_update.return_value = Mock(spec = TelegramDomainMapper.Result)
        self.telegram_data_resolver.resolve.return_value = Mock(
            spec = TelegramDataResolver.Result,
            chat = Mock(spec = ChatConfig, chat_id = "123"),
            author = None,
        )

        error_message = "Test error"
        error_response = [Mock(chat_id = "123", text = "Error response")]
        self.chat_messages_dao.get_latest_chat_messages.side_effect = Exception(error_message)
        self.domain_langchain_mapper.map_bot_message_to_storage.return_value = error_response

        with patch("features.prompting.prompt_library.error_general_problem") as mock_error:
            mock_error.return_value = "Error response"

            result = respond_to_update(self.update)

            self.assertFalse(result)
            mock_error.assert_called_once_with(error_message)
            # noinspection PyUnresolvedReferences
            self.domain_langchain_mapper.map_bot_message_to_storage.assert_called_once()
            # noinspection PyUnresolvedReferences
            self.telegram_bot_sdk.send_text_message.assert_called_once_with("123", "Error response")
