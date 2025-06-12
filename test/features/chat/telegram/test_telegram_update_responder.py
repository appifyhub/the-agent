import unittest
from unittest.mock import Mock, patch

from api.settings_controller import SettingsController
from db.crud.chat_config import ChatConfigCRUD
from db.crud.chat_message import ChatMessageCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.sql_util import SQLUtil
from features.chat.sponsorship_manager import SponsorshipManager
from features.chat.telegram.domain_langchain_mapper import DomainLangchainMapper
from features.chat.telegram.model.update import Update
from features.chat.telegram.sdk.telegram_bot_api import TelegramBotAPI
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.chat.telegram.telegram_data_resolver import TelegramDataResolver
from features.chat.telegram.telegram_domain_mapper import TelegramDomainMapper
from features.chat.telegram.telegram_update_responder import respond_to_update


class TelegramUpdateResponderTest(unittest.TestCase):
    user_dao: UserCRUD
    sponsorship_dao: SponsorshipCRUD
    sponsorship_manager: SponsorshipManager
    chat_messages_dao: ChatMessageCRUD
    chat_config_dao: ChatConfigCRUD
    settings_controller: SettingsController
    telegram_domain_mapper: TelegramDomainMapper
    telegram_data_resolver: TelegramDataResolver
    domain_langchain_mapper: DomainLangchainMapper
    telegram_bot_sdk: TelegramBotSDK
    update: Update
    sql: SQLUtil

    def setUp(self):
        # create all the mocks
        self.user_dao = Mock(spec = UserCRUD)
        self.sponsorship_dao = Mock(spec = SponsorshipCRUD)
        self.sponsorship_manager = Mock(spec = SponsorshipManager)
        self.chat_messages_dao = Mock(spec = ChatMessageCRUD)
        self.chat_config_dao = Mock(spec = ChatConfigCRUD)
        self.settings_controller = Mock(spec = SettingsController)
        self.telegram_domain_mapper = Mock(spec = TelegramDomainMapper)
        self.telegram_data_resolver = Mock(spec = TelegramDataResolver)
        self.domain_langchain_mapper = Mock(spec = DomainLangchainMapper)
        self.telegram_bot_sdk = Mock(spec = TelegramBotSDK)
        self.telegram_bot_sdk.api = Mock(spec = TelegramBotAPI)
        self.update = Mock(spec = Update)
        self.sql = SQLUtil()
        # patch all dependencies in the correct namespace where they are used in telegram_update_responder
        patcher_get_detached_session = patch("features.chat.telegram.telegram_update_responder.get_detached_session")
        self.addCleanup(patcher_get_detached_session.stop)
        self.mock_get_detached_session = patcher_get_detached_session.start()
        self.mock_get_detached_session.return_value.__enter__.return_value = self.sql.start_session()
        patcher_user_crud = patch(
            "features.chat.telegram.telegram_update_responder.UserCRUD",
            return_value = self.user_dao,
        )
        patcher_sponsorship_crud = patch(
            "features.chat.telegram.telegram_update_responder.SponsorshipCRUD",
            return_value = self.sponsorship_dao,
        )
        patcher_sponsorship_manager = patch(
            "features.chat.telegram.telegram_update_responder.SponsorshipManager",
            return_value = self.sponsorship_manager,
        )
        patcher_chat_message_crud = patch(
            "features.chat.telegram.telegram_update_responder.ChatMessageCRUD",
            return_value = self.chat_messages_dao,
        )
        patcher_chat_config_crud = patch(
            "features.chat.telegram.telegram_update_responder.ChatConfigCRUD",
            return_value = self.chat_config_dao,
        )
        patcher_settings_controller = patch(
            "features.chat.telegram.telegram_update_responder.SettingsController",
            return_value = self.settings_controller,
        )
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
        # start the patchers
        patcher_user_crud.start()
        patcher_sponsorship_crud.start()
        patcher_sponsorship_manager.start()
        patcher_chat_message_crud.start()
        patcher_chat_config_crud.start()
        patcher_settings_controller.start()
        patcher_telegram_bot_sdk.start()
        patcher_telegram_domain_mapper.start()
        patcher_domain_langchain_mapper.start()
        patcher_telegram_data_resolver.start()

        # make sure to stop the patchers after the test
        self.addCleanup(patcher_user_crud.stop)
        self.addCleanup(patcher_sponsorship_crud.stop)
        self.addCleanup(patcher_sponsorship_manager.stop)
        self.addCleanup(patcher_chat_message_crud.stop)
        self.addCleanup(patcher_chat_config_crud.stop)
        self.addCleanup(patcher_settings_controller.stop)
        self.addCleanup(patcher_telegram_bot_sdk.stop)
        self.addCleanup(patcher_telegram_domain_mapper.stop)
        self.addCleanup(patcher_domain_langchain_mapper.stop)
        self.addCleanup(patcher_telegram_data_resolver.stop)

    def tearDown(self):
        self.sql.end_session()

    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.execute")
    def test_successful_response(self, mock_execute):
        mock_execute.return_value = Mock(content = "Test response")

        self.telegram_domain_mapper.map_update.return_value = Mock()
        self.telegram_data_resolver.resolve.return_value = Mock(
            chat = Mock(chat_id = "123"),
            author = Mock(),
        )
        self.chat_messages_dao.get_latest_chat_messages.return_value = []

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
        self.telegram_domain_mapper.map_update.return_value = Mock()
        self.telegram_data_resolver.resolve.return_value = Mock(
            chat = Mock(chat_id = "123"),
            author = Mock(),
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
        self.telegram_domain_mapper.map_update.return_value = Mock()
        self.telegram_data_resolver.resolve.return_value = Mock(
            chat = Mock(chat_id = "123"),
            author = None
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
