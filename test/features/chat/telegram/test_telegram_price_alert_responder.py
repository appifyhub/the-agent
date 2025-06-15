import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from db.crud.chat_config import ChatConfigCRUD
from db.crud.price_alert import PriceAlertCRUD
from db.crud.tools_cache import ToolsCacheCRUD
from db.crud.user import UserCRUD
from features.chat.price_alert_manager import DATETIME_PRINT_FORMAT, PriceAlertManager
from features.chat.telegram.sdk.telegram_bot_api import TelegramBotAPI
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.chat.telegram.telegram_price_alert_responder import respond_with_announcements
from util.translations_cache import TranslationsCache


class TelegramPriceAlertResponderTest(unittest.TestCase):
    user_dao: UserCRUD
    chat_config_dao: ChatConfigCRUD
    price_alert_dao: PriceAlertCRUD
    tools_cache_dao: ToolsCacheCRUD
    telegram_bot_sdk: TelegramBotSDK
    translations: TranslationsCache

    def setUp(self):
        self.user_dao = Mock(spec = UserCRUD)
        self.chat_config_dao = Mock(spec = ChatConfigCRUD)
        self.price_alert_dao = Mock(spec = PriceAlertCRUD)
        self.tools_cache_dao = Mock(spec = ToolsCacheCRUD)
        self.telegram_bot_sdk = Mock(spec = TelegramBotSDK)
        self.telegram_bot_sdk.api = Mock(spec = TelegramBotAPI)
        self.translations = Mock(spec = TranslationsCache)

    # noinspection PyUnusedLocal
    @patch("features.chat.telegram.telegram_price_alert_responder.ExchangeRateFetcher")
    @patch("features.chat.telegram.telegram_price_alert_responder.PriceAlertManager.check_triggered_alerts")
    @patch("features.chat.telegram.telegram_price_alert_responder.InformationAnnouncer")
    def test_successful_announcements(self, mock_announcer, mock_check_alerts, mock_rate_fetcher):
        # Create actual TriggeredAlert objects
        triggered_alerts = [
            PriceAlertManager.TriggeredAlert(
                chat_id = "123", base_currency = "BTC", desired_currency = "USD", threshold_percent = 5,
                old_rate = 10000, old_rate_time = datetime(2023, 1, 1).strftime(DATETIME_PRINT_FORMAT),
                new_rate = 11000, new_rate_time = datetime(2023, 1, 2).strftime(DATETIME_PRINT_FORMAT),
                price_change_percent = 10,
            ),
            PriceAlertManager.TriggeredAlert(
                chat_id = "456", base_currency = "ETH", desired_currency = "EUR", threshold_percent = 3,
                old_rate = 2000, old_rate_time = datetime(2023, 1, 1).strftime(DATETIME_PRINT_FORMAT),
                new_rate = 2100, new_rate_time = datetime(2023, 1, 2).strftime(DATETIME_PRINT_FORMAT),
                price_change_percent = 5,
            ),
        ]
        mock_check_alerts.return_value = triggered_alerts

        self.chat_config_dao.get.side_effect = [
            {"chat_id": "123", "language_name": "English", "language_iso_code": "en"},
            {"chat_id": "456", "language_name": "Spanish", "language_iso_code": "es"},
        ]

        mock_announcer_instance = Mock()
        mock_announcer_instance.execute.return_value = Mock(content = "Test announcement")
        mock_announcer.return_value = mock_announcer_instance

        self.translations.get.side_effect = [None, None]  # Force new announcements to be created
        self.translations.save.return_value = "Test announcement"

        result = respond_with_announcements(
            self.user_dao,
            self.chat_config_dao,
            self.price_alert_dao,
            self.tools_cache_dao,
            self.telegram_bot_sdk,
            self.translations,
        )

        self.assertEqual(result["alerts_triggered"], 2)
        self.assertEqual(result["announcements_created"], 2)  # Now expecting 2 announcements
        self.assertEqual(result["chats_affected"], 2)
        self.assertEqual(result["chats_notified"], 2)

        self.assertEqual(mock_announcer.call_count, 2)
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.telegram_bot_sdk.send_text_message.call_count, 2)

    # noinspection PyUnusedLocal
    @patch("features.chat.telegram.telegram_price_alert_responder.ExchangeRateFetcher")
    @patch("features.chat.telegram.telegram_price_alert_responder.PriceAlertManager.check_triggered_alerts")
    def test_no_triggered_alerts(self, mock_check_alerts, mock_rate_fetcher):
        mock_check_alerts.return_value = []

        result = respond_with_announcements(
            self.user_dao,
            self.chat_config_dao,
            self.price_alert_dao,
            self.tools_cache_dao,
            self.telegram_bot_sdk,
            self.translations,
        )

        self.assertEqual(result["alerts_triggered"], 0)
        self.assertEqual(result["announcements_created"], 0)
        self.assertEqual(result["chats_affected"], 0)
        self.assertEqual(result["chats_notified"], 0)
        # noinspection PyUnresolvedReferences
        self.telegram_bot_sdk.send_text_message.assert_not_called()

    # noinspection PyUnusedLocal
    @patch("features.chat.telegram.telegram_price_alert_responder.ExchangeRateFetcher")
    @patch("features.chat.telegram.telegram_price_alert_responder.PriceAlertManager.check_triggered_alerts")
    @patch("features.chat.telegram.telegram_price_alert_responder.InformationAnnouncer")
    def test_announcement_creation_failure(self, mock_announcer, mock_check_alerts, mock_rate_fetcher):
        mock_check_alerts.return_value = [
            Mock(chat_id = "123", base_currency = "BTC", desired_currency = "USD", threshold_percent = 5),
        ]

        self.chat_config_dao.get.return_value = {
            "chat_id": "123",
            "language_name": "English",
            "language_iso_code": "en",
        }

        mock_announcer_instance = Mock()
        mock_announcer_instance.execute.side_effect = Exception("Announcement creation failed")
        mock_announcer.return_value = mock_announcer_instance

        self.translations.get.return_value = None  # Force new announcement to be created

        result = respond_with_announcements(
            self.user_dao,
            self.chat_config_dao,
            self.price_alert_dao,
            self.tools_cache_dao,
            self.telegram_bot_sdk,
            self.translations,
        )

        self.assertEqual(result["alerts_triggered"], 1)
        self.assertEqual(result["announcements_created"], 0)
        self.assertEqual(result["chats_affected"], 1)
        self.assertEqual(result["chats_notified"], 0)
        # noinspection PyUnresolvedReferences
        self.telegram_bot_sdk.send_text_message.assert_not_called()

    # noinspection PyUnusedLocal
    @patch("features.chat.telegram.telegram_price_alert_responder.ExchangeRateFetcher")
    @patch("features.chat.telegram.telegram_price_alert_responder.PriceAlertManager.check_triggered_alerts")
    def test_notification_failure(self, mock_check_alerts, mock_rate_fetcher):
        mock_check_alerts.return_value = [
            Mock(chat_id = "123", base_currency = "BTC", desired_currency = "USD", threshold_percent = 5),
        ]

        self.chat_config_dao.get.return_value = {
            "chat_id": "123",
            "language_name": "English",
            "language_iso_code": "en",
        }
        self.translations.get.return_value = "Cached announcement"
        self.telegram_bot_sdk.send_text_message.side_effect = Exception("Notification failed")

        result = respond_with_announcements(
            self.user_dao,
            self.chat_config_dao,
            self.price_alert_dao,
            self.tools_cache_dao,
            self.telegram_bot_sdk,
            self.translations,
        )

        self.assertEqual(result["alerts_triggered"], 1)
        self.assertEqual(result["announcements_created"], 0)
        self.assertEqual(result["chats_affected"], 1)
        self.assertEqual(result["chats_notified"], 0)
        # noinspection PyUnresolvedReferences
        self.telegram_bot_sdk.send_text_message.assert_called_once()

    # noinspection PyUnusedLocal
    @patch("features.chat.telegram.telegram_price_alert_responder.ExchangeRateFetcher")
    @patch("features.chat.telegram.telegram_price_alert_responder.PriceAlertManager.check_triggered_alerts")
    def test_cached_announcement(self, mock_check_alerts, mock_rate_fetcher):
        mock_check_alerts.return_value = [
            Mock(chat_id = "123", base_currency = "BTC", desired_currency = "USD", threshold_percent = 5),
        ]

        self.chat_config_dao.get.return_value = {
            "chat_id": "123",
            "language_name": "English",
            "language_iso_code": "en",
        }
        self.translations.get.return_value = "Cached announcement"

        result = respond_with_announcements(
            self.user_dao,
            self.chat_config_dao,
            self.price_alert_dao,
            self.tools_cache_dao,
            self.telegram_bot_sdk,
            self.translations,
        )

        self.assertEqual(result["alerts_triggered"], 1)
        self.assertEqual(result["announcements_created"], 0)
        self.assertEqual(result["chats_affected"], 1)
        self.assertEqual(result["chats_notified"], 1)
        # noinspection PyUnresolvedReferences
        self.telegram_bot_sdk.send_text_message.assert_called_once_with("123", "Cached announcement")
