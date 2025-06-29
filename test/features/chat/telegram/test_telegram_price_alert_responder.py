import unittest
from datetime import datetime
from unittest.mock import Mock, patch
from uuid import UUID

from db.crud.chat_config import ChatConfigCRUD
from db.crud.price_alert import PriceAlertCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.tools_cache import ToolsCacheCRUD
from db.crud.user import UserCRUD
from db.model.chat_config import ChatConfigDB
from features.announcements.information_announcer import InformationAnnouncer
from features.chat.price_alert_manager import DATETIME_PRINT_FORMAT, PriceAlertManager
from features.chat.telegram.sdk.telegram_bot_api import TelegramBotAPI
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.chat.telegram.telegram_price_alert_responder import respond_with_price_alerts
from util.translations_cache import TranslationsCache


class TelegramPriceAlertResponderTest(unittest.TestCase):
    user_dao: UserCRUD
    chat_config_dao: ChatConfigCRUD
    price_alert_dao: PriceAlertCRUD
    tools_cache_dao: ToolsCacheCRUD
    sponsorship_dao: SponsorshipCRUD
    telegram_bot_sdk: TelegramBotSDK
    translations: TranslationsCache

    def setUp(self):
        self.user_dao = Mock(spec = UserCRUD)
        self.chat_config_dao = Mock(spec = ChatConfigCRUD)
        self.price_alert_dao = Mock(spec = PriceAlertCRUD)
        self.tools_cache_dao = Mock(spec = ToolsCacheCRUD)
        self.sponsorship_dao = Mock(spec = SponsorshipCRUD)
        self.telegram_bot_sdk = Mock(spec = TelegramBotSDK)
        self.telegram_bot_sdk.api = Mock(spec = TelegramBotAPI)
        self.translations = Mock(spec = TranslationsCache)

    # noinspection PyUnusedLocal
    @patch("features.chat.telegram.telegram_price_alert_responder.PriceAlertManager")
    @patch("features.chat.telegram.telegram_price_alert_responder.InformationAnnouncer")
    def test_successful_announcements(self, mock_announcer, mock_alert_manager_class):
        # Create actual TriggeredAlert objects
        test_owner_id = UUID(int = 1)
        triggered_alerts = [
            PriceAlertManager.TriggeredAlert(
                chat_id = "123", owner_id = test_owner_id,
                base_currency = "BTC", desired_currency = "USD", threshold_percent = 5,
                old_rate = 10000, old_rate_time = datetime(2023, 1, 1).strftime(DATETIME_PRINT_FORMAT),
                new_rate = 11000, new_rate_time = datetime(2023, 1, 2).strftime(DATETIME_PRINT_FORMAT),
                price_change_percent = 10,
            ),
            PriceAlertManager.TriggeredAlert(
                chat_id = "456", owner_id = test_owner_id,
                base_currency = "ETH", desired_currency = "EUR", threshold_percent = 3,
                old_rate = 2000, old_rate_time = datetime(2023, 1, 1).strftime(DATETIME_PRINT_FORMAT),
                new_rate = 2100, new_rate_time = datetime(2023, 1, 2).strftime(DATETIME_PRINT_FORMAT),
                price_change_percent = 5,
            ),
        ]

        # Mock the PriceAlertManager instance and its methods
        mock_alert_manager = Mock(spec = PriceAlertManager)
        mock_alert_manager.get_triggered_alerts.return_value = triggered_alerts
        mock_alert_manager_class.return_value = mock_alert_manager

        # Mock the chat config responses
        mock_chat_config_db = ChatConfigDB(
            chat_id = "123",
            title = "Test Chat",
            is_private = False,
            reply_chance_percent = 100,
            release_notifications = ChatConfigDB.ReleaseNotifications.all,
            language_name = "English",
            language_iso_code = "en",
        )
        self.chat_config_dao.get.return_value = mock_chat_config_db

        # Mock the announcer to return content
        mock_announcer_instance = Mock(spec = InformationAnnouncer)
        mock_announcer_instance.execute.return_value = Mock(content = "Test announcement")
        mock_announcer.return_value = mock_announcer_instance

        # Force new announcements to be created
        self.translations.get.side_effect = [None, None]  # Force new announcements to be created
        self.translations.save.return_value = "Test announcement"

        result = respond_with_price_alerts(
            self.user_dao,
            self.chat_config_dao,
            self.price_alert_dao,
            self.tools_cache_dao,
            self.sponsorship_dao,
            self.telegram_bot_sdk,
        )

        # Assertions
        self.assertEqual(result["alerts_triggered"], 2)
        self.assertEqual(result["chats_notified"], 2)
        self.assertEqual(result["announcements_created"], 2)
        self.assertEqual(result["chats_affected"], 2)

        # Verify PriceAlertManager was created correctly
        mock_alert_manager_class.assert_called_once()
        # Verify the mock methods were called
        mock_alert_manager.get_triggered_alerts.assert_called_once()
        # Verify announcements were sent
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.telegram_bot_sdk.send_text_message.call_count, 2)

    # noinspection PyUnusedLocal
    @patch("features.chat.telegram.telegram_price_alert_responder.PriceAlertManager")
    def test_no_triggered_alerts(self, mock_alert_manager_class):
        # Mock the PriceAlertManager instance to return no alerts
        mock_alert_manager = Mock(spec = PriceAlertManager)
        mock_alert_manager.get_triggered_alerts.return_value = []
        mock_alert_manager_class.return_value = mock_alert_manager

        result = respond_with_price_alerts(
            self.user_dao,
            self.chat_config_dao,
            self.price_alert_dao,
            self.tools_cache_dao,
            self.sponsorship_dao,
            self.telegram_bot_sdk,
        )

        # Assertions
        self.assertEqual(result["alerts_triggered"], 0)
        self.assertEqual(result["chats_notified"], 0)
        self.assertEqual(result["announcements_created"], 0)
        self.assertEqual(result["chats_affected"], 0)
        # noinspection PyUnresolvedReferences
        self.telegram_bot_sdk.send_text_message.assert_not_called()

    # noinspection PyUnusedLocal
    @patch("features.chat.telegram.telegram_price_alert_responder.PriceAlertManager")
    @patch("features.chat.telegram.telegram_price_alert_responder.InformationAnnouncer")
    def test_announcement_creation_failure(self, mock_announcer, mock_alert_manager_class):
        test_owner_id = UUID(int = 1)
        triggered_alerts = [
            PriceAlertManager.TriggeredAlert(
                chat_id = "123", owner_id = test_owner_id,
                base_currency = "BTC", desired_currency = "USD", threshold_percent = 5,
                old_rate = 10000, old_rate_time = datetime(2023, 1, 1).strftime(DATETIME_PRINT_FORMAT),
                new_rate = 11000, new_rate_time = datetime(2023, 1, 2).strftime(DATETIME_PRINT_FORMAT),
                price_change_percent = 10,
            ),
        ]

        # Mock the PriceAlertManager instance
        mock_alert_manager = Mock(spec = PriceAlertManager)
        mock_alert_manager.get_triggered_alerts.return_value = triggered_alerts
        mock_alert_manager_class.return_value = mock_alert_manager

        # Mock the chat config response
        mock_chat_config_db = ChatConfigDB(
            chat_id = "123",
            title = "Test Chat",
            is_private = False,
            reply_chance_percent = 100,
            release_notifications = ChatConfigDB.ReleaseNotifications.all,
            language_name = "English",
            language_iso_code = "en",
        )
        self.chat_config_dao.get.return_value = mock_chat_config_db

        # Mock the announcer to return no content (failure)
        mock_announcer_instance = Mock(spec = InformationAnnouncer)
        mock_announcer_instance.execute.return_value = Mock(content = None)
        mock_announcer.return_value = mock_announcer_instance

        self.translations.get.return_value = None  # Force new announcement to be created

        result = respond_with_price_alerts(
            self.user_dao,
            self.chat_config_dao,
            self.price_alert_dao,
            self.tools_cache_dao,
            self.sponsorship_dao,
            self.telegram_bot_sdk,
        )

        # Assertions - no announcements created due to failure
        self.assertEqual(result["alerts_triggered"], 1)
        self.assertEqual(result["chats_notified"], 0)
        self.assertEqual(result["announcements_created"], 0)
        self.assertEqual(result["chats_affected"], 1)
        # noinspection PyUnresolvedReferences
        self.telegram_bot_sdk.send_text_message.assert_not_called()

    # noinspection PyUnusedLocal
    @patch("features.chat.telegram.telegram_price_alert_responder.TranslationsCache")
    @patch("features.chat.telegram.telegram_price_alert_responder.PriceAlertManager")
    def test_notification_failure(self, mock_alert_manager_class, mock_translations_cache_class):
        # Create actual TriggeredAlert objects
        test_owner_id = UUID(int = 1)
        triggered_alerts = [
            PriceAlertManager.TriggeredAlert(
                chat_id = "123", owner_id = test_owner_id,
                base_currency = "BTC", desired_currency = "USD", threshold_percent = 5,
                old_rate = 10000, old_rate_time = datetime(2023, 1, 1).strftime(DATETIME_PRINT_FORMAT),
                new_rate = 11000, new_rate_time = datetime(2023, 1, 2).strftime(DATETIME_PRINT_FORMAT),
                price_change_percent = 10,
            ),
        ]

        # Mock the PriceAlertManager instance
        mock_alert_manager = Mock(spec = PriceAlertManager)
        mock_alert_manager.get_triggered_alerts.return_value = triggered_alerts
        mock_alert_manager_class.return_value = mock_alert_manager

        # Mock the chat config response
        mock_chat_config_db = ChatConfigDB(
            chat_id = "123",
            title = "Test Chat",
            is_private = False,
            reply_chance_percent = 100,
            release_notifications = ChatConfigDB.ReleaseNotifications.all,
            language_name = "English",
            language_iso_code = "en",
        )
        self.chat_config_dao.get.return_value = mock_chat_config_db

        # Mock the TranslationsCache to return cached content
        mock_translations_cache = Mock(spec = TranslationsCache)
        mock_translations_cache.get.return_value = "Cached announcement"
        mock_translations_cache_class.return_value = mock_translations_cache

        self.telegram_bot_sdk.send_text_message.side_effect = Exception("Notification failed")

        result = respond_with_price_alerts(
            self.user_dao,
            self.chat_config_dao,
            self.price_alert_dao,
            self.tools_cache_dao,
            self.sponsorship_dao,
            self.telegram_bot_sdk,
        )

        self.assertEqual(result["alerts_triggered"], 1)
        self.assertEqual(result["announcements_created"], 0)
        self.assertEqual(result["chats_affected"], 1)
        self.assertEqual(result["chats_notified"], 0)
        # noinspection PyUnresolvedReferences
        self.telegram_bot_sdk.send_text_message.assert_called_once()

    # noinspection PyUnusedLocal
    @patch("features.chat.telegram.telegram_price_alert_responder.TranslationsCache")
    @patch("features.chat.telegram.telegram_price_alert_responder.PriceAlertManager")
    def test_cached_announcement(self, mock_alert_manager_class, mock_translations_cache_class):
        # Create actual TriggeredAlert objects
        test_owner_id = UUID(int = 1)
        triggered_alerts = [
            PriceAlertManager.TriggeredAlert(
                chat_id = "123", owner_id = test_owner_id,
                base_currency = "BTC", desired_currency = "USD", threshold_percent = 5,
                old_rate = 10000, old_rate_time = datetime(2023, 1, 1).strftime(DATETIME_PRINT_FORMAT),
                new_rate = 11000, new_rate_time = datetime(2023, 1, 2).strftime(DATETIME_PRINT_FORMAT),
                price_change_percent = 10,
            ),
        ]

        # Mock the PriceAlertManager instance
        mock_alert_manager = Mock(spec = PriceAlertManager)
        mock_alert_manager.get_triggered_alerts.return_value = triggered_alerts
        mock_alert_manager_class.return_value = mock_alert_manager

        # Mock the chat config response
        mock_chat_config_db = ChatConfigDB(
            chat_id = "123",
            title = "Test Chat",
            is_private = False,
            reply_chance_percent = 100,
            release_notifications = ChatConfigDB.ReleaseNotifications.all,
            language_name = "English",
            language_iso_code = "en",
        )
        self.chat_config_dao.get.return_value = mock_chat_config_db

        # Mock the TranslationsCache to return cached content
        mock_translations_cache = Mock(spec = TranslationsCache)
        mock_translations_cache.get.return_value = "Cached announcement"
        mock_translations_cache_class.return_value = mock_translations_cache

        result = respond_with_price_alerts(
            self.user_dao,
            self.chat_config_dao,
            self.price_alert_dao,
            self.tools_cache_dao,
            self.sponsorship_dao,
            self.telegram_bot_sdk,
        )

        # Assertions
        self.assertEqual(result["alerts_triggered"], 1)
        self.assertEqual(result["chats_notified"], 1)
        self.assertEqual(result["announcements_created"], 0)
        self.assertEqual(result["chats_affected"], 1)
        # noinspection PyUnresolvedReferences
        self.telegram_bot_sdk.send_text_message.assert_called_once_with("123", "Cached announcement")
