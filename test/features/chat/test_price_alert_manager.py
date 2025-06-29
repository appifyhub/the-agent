import unittest
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID

from db.crud.chat_config import ChatConfigCRUD
from db.crud.price_alert import PriceAlertCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.tools_cache import ToolsCacheCRUD
from db.crud.user import UserCRUD
from db.model.user import UserDB
from db.schema.chat_config import ChatConfig
from db.schema.price_alert import PriceAlert
from db.schema.user import User
from features.chat.price_alert_manager import PriceAlertManager
from features.currencies.exchange_rate_fetcher import ExchangeRateFetcher


class PriceAlertManagerTest(unittest.TestCase):
    mock_user_dao: UserCRUD
    mock_chat_config_dao: ChatConfigCRUD
    mock_price_alert_dao: PriceAlertCRUD
    mock_tools_cache_dao: ToolsCacheCRUD
    mock_sponsorship_dao: SponsorshipCRUD
    mock_exchange_rate_fetcher: ExchangeRateFetcher

    chat_id: str
    user_id: str
    user: User
    chat_config: ChatConfig

    def setUp(self):
        self.mock_user_dao = MagicMock(spec = UserCRUD)
        self.mock_chat_config_dao = MagicMock(spec = ChatConfigCRUD)
        self.mock_price_alert_dao = MagicMock(spec = PriceAlertCRUD)
        self.mock_tools_cache_dao = MagicMock(spec = ToolsCacheCRUD)
        self.mock_sponsorship_dao = MagicMock(spec = SponsorshipCRUD)
        self.mock_exchange_rate_fetcher = MagicMock(spec = ExchangeRateFetcher)

        self.chat_id = "test_chat_id"
        self.user_id = UUID(int = 1).hex
        self.user = User(
            id = UUID(hex = self.user_id),
            full_name = "Test User",
            telegram_username = "test_username",
            telegram_chat_id = "test_chat_id",
            telegram_user_id = 1,
            open_ai_key = "test_api_key",
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.chat_config = ChatConfig(chat_id = self.chat_id)

        self.mock_user_dao.get.return_value = self.user
        self.mock_chat_config_dao.get.return_value = self.chat_config

    def test_initialization_invalid_chat(self):
        self.mock_chat_config_dao.get.return_value = None
        with self.assertRaises(ValueError):
            PriceAlertManager(
                self.chat_id,
                self.user_id,
                self.mock_user_dao,
                self.mock_chat_config_dao,
                self.mock_price_alert_dao,
                self.mock_tools_cache_dao,
                self.mock_sponsorship_dao,
            )

    def test_initialization_invalid_user(self):
        self.mock_user_dao.get.return_value = None
        with self.assertRaises(ValueError):
            PriceAlertManager(
                self.chat_id,
                self.user_id,
                self.mock_user_dao,
                self.mock_chat_config_dao,
                self.mock_price_alert_dao,
                self.mock_tools_cache_dao,
                self.mock_sponsorship_dao,
            )

    def test_create_alert(self):
        manager = PriceAlertManager(
            self.chat_id,
            self.user_id,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_price_alert_dao,
            self.mock_tools_cache_dao,
            self.mock_sponsorship_dao,
        )
        # Mock the cache to return None for cache miss
        self.mock_tools_cache_dao.get.return_value = None
        # Mock the price alert DAO save method
        self.mock_price_alert_dao.save.return_value = PriceAlert(
            chat_id = self.chat_id,
            owner_id = UUID(hex = self.user_id),
            base_currency = "BTC",
            desired_currency = "USD",
            threshold_percent = 5,
            last_price = 1.5,
            last_price_time = datetime.now(),
        )

        # Mock the ExchangeRateFetcher by patching it
        with patch("features.chat.price_alert_manager.ExchangeRateFetcher") as mock_fetcher_class:
            mock_fetcher = Mock(spec = ExchangeRateFetcher)
            mock_fetcher.execute.return_value = {"rate": 1.5}
            mock_fetcher_class.return_value = mock_fetcher
            alert = manager.create_alert("BTC", "USD", 5)

        self.assertEqual(alert.chat_id, self.chat_id)
        self.assertEqual(alert.base_currency, "BTC")
        self.assertEqual(alert.desired_currency, "USD")
        self.assertEqual(alert.threshold_percent, 5)
        self.assertEqual(alert.last_price, 1.5)
        # noinspection PyUnresolvedReferences
        self.mock_price_alert_dao.save.assert_called_once()

    def test_get_all_alerts(self):
        manager = PriceAlertManager(
            self.chat_id,
            self.user_id,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_price_alert_dao,
            self.mock_tools_cache_dao,
            self.mock_sponsorship_dao,
        )
        mock_alerts = [
            PriceAlert(
                chat_id = self.chat_id,
                owner_id = UUID(hex = self.user_id),
                base_currency = "BTC",
                desired_currency = "USD",
                threshold_percent = 5,
                last_price = 1000,
                last_price_time = datetime.now(),
            ),
            PriceAlert(
                chat_id = self.chat_id,
                owner_id = UUID(hex = self.user_id),
                base_currency = "ETH",
                desired_currency = "EUR",
                threshold_percent = 3,
                last_price = 2000,
                last_price_time = datetime.now(),
            ),
        ]
        self.mock_price_alert_dao.get_alerts_by_chat.return_value = mock_alerts

        alerts = manager.get_active_alerts()
        self.assertEqual(len(alerts), 2)
        self.assertEqual(alerts[0].base_currency, "BTC")
        self.assertEqual(alerts[1].base_currency, "ETH")

    def test_delete_alert(self):
        manager = PriceAlertManager(
            self.chat_id,
            self.user_id,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_price_alert_dao,
            self.mock_tools_cache_dao,
            self.mock_sponsorship_dao,
        )
        mock_deleted_alert = PriceAlert(
            chat_id = self.chat_id,
            owner_id = UUID(hex = self.user_id),
            base_currency = "BTC",
            desired_currency = "USD",
            threshold_percent = 5,
            last_price = 1000,
            last_price_time = datetime.now(),
        )
        self.mock_price_alert_dao.delete.return_value = mock_deleted_alert

        deleted_alert = manager.delete_alert("BTC", "USD")
        self.assertIsNotNone(deleted_alert)
        self.assertEqual(deleted_alert.base_currency, "BTC")
        self.assertEqual(deleted_alert.desired_currency, "USD")
        # noinspection PyUnresolvedReferences
        self.mock_price_alert_dao.delete.assert_called_once()

    def test_check_alerts(self):
        manager = PriceAlertManager(
            self.chat_id,
            self.user_id,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_price_alert_dao,
            self.mock_tools_cache_dao,
            self.mock_sponsorship_dao,
        )
        mock_alerts = [
            PriceAlert(
                chat_id = self.chat_id,
                owner_id = UUID(hex = self.user_id),
                base_currency = "BTC",
                desired_currency = "USD",
                threshold_percent = 5,
                last_price = 1000,
                last_price_time = datetime.now(),
            ),
            PriceAlert(
                chat_id = self.chat_id,
                owner_id = UUID(hex = self.user_id),
                base_currency = "ETH",
                desired_currency = "EUR",
                threshold_percent = 3,
                last_price = 2000,
                last_price_time = datetime.now(),
            ),
        ]
        self.mock_price_alert_dao.get_alerts_by_chat.return_value = mock_alerts
        self.mock_tools_cache_dao.get.return_value = None

        with patch.object(PriceAlertManager, "get_triggered_alerts") as mock_get:
            mock_get.return_value = [
                PriceAlertManager.TriggeredAlert(
                    chat_id = self.chat_id,
                    owner_id = UUID(hex = self.user_id),
                    base_currency = "BTC",
                    desired_currency = "USD",
                    threshold_percent = 5,
                    old_rate = 1000,
                    old_rate_time = "2023-01-01 00:00 UTC",
                    new_rate = 1100,
                    new_rate_time = "2023-01-02 00:00 UTC",
                    price_change_percent = 10,
                ),
            ]
            triggered_alerts = manager.get_triggered_alerts()

        self.assertEqual(len(triggered_alerts), 1)
        self.assertEqual(triggered_alerts[0].base_currency, "BTC")
        self.assertEqual(triggered_alerts[0].desired_currency, "USD")
        self.assertEqual(triggered_alerts[0].price_change_percent, 10)

    def test_check_alerts_with_zero_last_price(self):
        manager = PriceAlertManager(
            self.chat_id,
            self.user_id,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_price_alert_dao,
            self.mock_tools_cache_dao,
            self.mock_sponsorship_dao,
        )
        mock_alerts = [
            PriceAlert(
                chat_id = self.chat_id,
                owner_id = UUID(hex = self.user_id),
                base_currency = "BTC",
                desired_currency = "USD",
                threshold_percent = 5,
                last_price = 0,
                last_price_time = datetime.now(),
            ),
        ]
        self.mock_price_alert_dao.get_alerts_by_chat.return_value = mock_alerts
        self.mock_tools_cache_dao.get.return_value = None

        with patch.object(PriceAlertManager, "get_triggered_alerts") as mock_get:
            mock_get.return_value = [
                PriceAlertManager.TriggeredAlert(
                    chat_id = self.chat_id,
                    owner_id = UUID(hex = self.user_id),
                    base_currency = "BTC",
                    desired_currency = "USD",
                    threshold_percent = 5,
                    old_rate = 0,
                    old_rate_time = "2023-01-01 00:00 UTC",
                    new_rate = 1000,
                    new_rate_time = "2023-01-02 00:00 UTC",
                    price_change_percent = 100000,
                ),
            ]
            triggered_alerts = manager.get_triggered_alerts()

        self.assertEqual(len(triggered_alerts), 1)
        self.assertEqual(triggered_alerts[0].base_currency, "BTC")
        self.assertEqual(triggered_alerts[0].desired_currency, "USD")
        self.assertEqual(triggered_alerts[0].price_change_percent, 100000)
