import unittest
from datetime import datetime, timedelta
from uuid import UUID

from db.sql_util import SQLUtil

from db.schema.chat_config import ChatConfigSave
from db.schema.price_alert import PriceAlertSave
from db.schema.user import UserSave


class PriceAlertCRUDTest(unittest.TestCase):
    sql: SQLUtil

    def setUp(self):
        self.sql = SQLUtil()

    def tearDown(self):
        self.sql.end_session()

    def _create_test_user(self) -> UUID:
        """Helper method to create a test user and return their ID"""
        user_db = self.sql.user_crud().create(
            UserSave(
                full_name = "Test User",
                telegram_username = "test_user",
                telegram_chat_id = "test_chat",
                telegram_user_id = 12345,
            ),
        )
        return user_db.id

    def test_create_price_alert(self):
        chat = self.sql.chat_config_crud().create(ChatConfigSave(chat_id = "chat1"))
        user_id = self._create_test_user()
        price_alert_data = PriceAlertSave(
            chat_id = chat.chat_id,
            owner_id = user_id,
            base_currency = "USD",
            desired_currency = "EUR",
            threshold_percent = 5,
            last_price = 0.85,
            last_price_time = datetime.now(),
        )

        price_alert = self.sql.price_alert_crud().create(price_alert_data)

        self.assertEqual(price_alert.chat_id, price_alert_data.chat_id)
        self.assertEqual(price_alert.base_currency, price_alert_data.base_currency)
        self.assertEqual(price_alert.desired_currency, price_alert_data.desired_currency)
        self.assertEqual(price_alert.threshold_percent, price_alert_data.threshold_percent)
        self.assertEqual(price_alert.last_price, price_alert_data.last_price)
        self.assertEqual(price_alert.last_price_time, price_alert_data.last_price_time)

    def test_get_price_alert(self):
        chat = self.sql.chat_config_crud().create(ChatConfigSave(chat_id = "chat1"))
        user_id = self._create_test_user()
        price_alert_data = PriceAlertSave(
            chat_id = chat.chat_id,
            owner_id = user_id,
            base_currency = "USD",
            desired_currency = "EUR",
            threshold_percent = 5,
            last_price = 0.85,
            last_price_time = datetime.now(),
        )
        created_price_alert = self.sql.price_alert_crud().create(price_alert_data)

        fetched_price_alert = self.sql.price_alert_crud().get(
            created_price_alert.chat_id,
            created_price_alert.base_currency,
            created_price_alert.desired_currency,
        )

        self.assertEqual(fetched_price_alert.chat_id, created_price_alert.chat_id)
        self.assertEqual(fetched_price_alert.base_currency, created_price_alert.base_currency)
        self.assertEqual(fetched_price_alert.desired_currency, created_price_alert.desired_currency)

    def test_get_all_price_alerts(self):
        chat1 = self.sql.chat_config_crud().create(ChatConfigSave(chat_id = "chat1"))
        chat2 = self.sql.chat_config_crud().create(ChatConfigSave(chat_id = "chat2"))
        user_id = self._create_test_user()
        price_alerts = [
            self.sql.price_alert_crud().create(
                PriceAlertSave(
                    chat_id = chat1.chat_id, owner_id = user_id,
                    base_currency = "USD", desired_currency = "EUR",
                    threshold_percent = 5, last_price = 0.85,
                ),
            ),
            self.sql.price_alert_crud().create(
                PriceAlertSave(
                    chat_id = chat2.chat_id, owner_id = user_id,
                    base_currency = "USD", desired_currency = "GBP",
                    threshold_percent = 3, last_price = 0.75,
                ),
            ),
        ]

        fetched_price_alerts = self.sql.price_alert_crud().get_all()

        self.assertEqual(len(fetched_price_alerts), len(price_alerts))
        for i in range(len(price_alerts)):
            self.assertEqual(fetched_price_alerts[i].chat_id, price_alerts[i].chat_id)
            self.assertEqual(fetched_price_alerts[i].base_currency, price_alerts[i].base_currency)
            self.assertEqual(fetched_price_alerts[i].desired_currency, price_alerts[i].desired_currency)

    def test_get_chat_alerts(self):
        chat1 = self.sql.chat_config_crud().create(ChatConfigSave(chat_id = "chat1"))
        chat2 = self.sql.chat_config_crud().create(ChatConfigSave(chat_id = "chat2"))

        user_id = self._create_test_user()
        chat1_alerts = [
            self.sql.price_alert_crud().create(
                PriceAlertSave(
                    chat_id = chat1.chat_id, owner_id = user_id,
                    base_currency = "USD", desired_currency = "EUR",
                    threshold_percent = 5, last_price = 0.85,
                ),
            ),
            self.sql.price_alert_crud().create(
                PriceAlertSave(
                    chat_id = chat1.chat_id, owner_id = user_id,
                    base_currency = "USD", desired_currency = "GBP",
                    threshold_percent = 3, last_price = 0.75,
                ),
            ),
        ]
        self.sql.price_alert_crud().create(
            PriceAlertSave(
                chat_id = chat2.chat_id, owner_id = user_id,
                base_currency = "USD", desired_currency = "JPY",
                threshold_percent = 2, last_price = 110.0,
            ),
        )

        fetched_chat1_alerts = self.sql.price_alert_crud().get_alerts_by_chat(chat1.chat_id)

        self.assertEqual(len(fetched_chat1_alerts), len(chat1_alerts))
        for i in range(len(chat1_alerts)):
            self.assertEqual(fetched_chat1_alerts[i].chat_id, chat1_alerts[i].chat_id)
            self.assertEqual(fetched_chat1_alerts[i].base_currency, chat1_alerts[i].base_currency)
            self.assertEqual(fetched_chat1_alerts[i].desired_currency, chat1_alerts[i].desired_currency)

    def test_update_price_alert(self):
        chat = self.sql.chat_config_crud().create(ChatConfigSave(chat_id = "chat1"))
        user_id = self._create_test_user()
        price_alert_data = PriceAlertSave(
            chat_id = chat.chat_id,
            owner_id = user_id,
            base_currency = "USD",
            desired_currency = "EUR",
            threshold_percent = 5,
            last_price = 0.85,
            last_price_time = datetime.now(),
        )
        created_price_alert = self.sql.price_alert_crud().create(price_alert_data)

        update_data = PriceAlertSave(
            chat_id = created_price_alert.chat_id,
            owner_id = created_price_alert.owner_id,
            base_currency = created_price_alert.base_currency,
            desired_currency = created_price_alert.desired_currency,
            threshold_percent = 7,
            last_price = 0.87,
            last_price_time = datetime.now() + timedelta(hours = 1),
        )
        updated_price_alert = self.sql.price_alert_crud().update(update_data)

        self.assertEqual(updated_price_alert.chat_id, created_price_alert.chat_id)
        self.assertEqual(updated_price_alert.base_currency, created_price_alert.base_currency)
        self.assertEqual(updated_price_alert.desired_currency, created_price_alert.desired_currency)
        self.assertEqual(updated_price_alert.threshold_percent, update_data.threshold_percent)
        self.assertEqual(updated_price_alert.last_price, update_data.last_price)
        self.assertEqual(updated_price_alert.last_price_time, update_data.last_price_time)

    def test_save_price_alert(self):
        chat = self.sql.chat_config_crud().create(ChatConfigSave(chat_id = "chat1"))
        user_id = self._create_test_user()
        price_alert_data = PriceAlertSave(
            chat_id = chat.chat_id,
            owner_id = user_id,
            base_currency = "USD",
            desired_currency = "EUR",
            threshold_percent = 5,
            last_price = 0.85,
            last_price_time = datetime.now(),
        )

        # First, save should create the record
        saved_price_alert = self.sql.price_alert_crud().save(price_alert_data)
        self.assertIsNotNone(saved_price_alert)
        self.assertEqual(saved_price_alert.chat_id, price_alert_data.chat_id)
        self.assertEqual(saved_price_alert.base_currency, price_alert_data.base_currency)
        self.assertEqual(saved_price_alert.desired_currency, price_alert_data.desired_currency)
        self.assertEqual(saved_price_alert.threshold_percent, price_alert_data.threshold_percent)
        self.assertEqual(saved_price_alert.last_price, price_alert_data.last_price)
        self.assertEqual(saved_price_alert.last_price_time, price_alert_data.last_price_time)

        # Now, save should update the existing record
        update_data = PriceAlertSave(
            chat_id = saved_price_alert.chat_id,
            owner_id = saved_price_alert.owner_id,
            base_currency = saved_price_alert.base_currency,
            desired_currency = saved_price_alert.desired_currency,
            threshold_percent = 7,
            last_price = 0.87,
            last_price_time = datetime.now() + timedelta(hours = 1),
        )
        updated_price_alert = self.sql.price_alert_crud().save(update_data)
        self.assertIsNotNone(updated_price_alert)
        self.assertEqual(updated_price_alert.chat_id, update_data.chat_id)
        self.assertEqual(updated_price_alert.base_currency, update_data.base_currency)
        self.assertEqual(updated_price_alert.desired_currency, update_data.desired_currency)
        self.assertEqual(updated_price_alert.threshold_percent, update_data.threshold_percent)
        self.assertEqual(updated_price_alert.last_price, update_data.last_price)
        self.assertEqual(updated_price_alert.last_price_time, update_data.last_price_time)

    def test_delete_price_alert(self):
        chat = self.sql.chat_config_crud().create(ChatConfigSave(chat_id = "chat1"))
        user_id = self._create_test_user()
        price_alert_data = PriceAlertSave(
            chat_id = chat.chat_id,
            owner_id = user_id,
            base_currency = "USD",
            desired_currency = "EUR",
            threshold_percent = 5,
            last_price = 0.85,
            last_price_time = datetime.now(),
        )
        created_price_alert = self.sql.price_alert_crud().create(price_alert_data)

        deleted_price_alert = self.sql.price_alert_crud().delete(
            created_price_alert.chat_id,
            created_price_alert.base_currency,
            created_price_alert.desired_currency,
        )

        self.assertEqual(deleted_price_alert.chat_id, created_price_alert.chat_id)
        self.assertEqual(deleted_price_alert.base_currency, created_price_alert.base_currency)
        self.assertEqual(deleted_price_alert.desired_currency, created_price_alert.desired_currency)
        self.assertIsNone(
            self.sql.price_alert_crud().get(
                created_price_alert.chat_id,
                created_price_alert.base_currency,
                created_price_alert.desired_currency,
            ),
        )
