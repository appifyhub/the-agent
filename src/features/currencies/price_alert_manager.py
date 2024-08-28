import math
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from db.crud.chat_config import ChatConfigCRUD
from db.crud.price_alert import PriceAlertCRUD
from db.crud.user import UserCRUD
from db.schema.chat_config import ChatConfig
from db.schema.price_alert import PriceAlert, PriceAlertSave
from db.schema.user import User
from features.currencies.exchange_rate_fetcher import ExchangeRateFetcher
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

DATE_TIME_PRINT_FORMAT = "%Y-%m-%d %H:%M %Z"


class PriceAlertManager(SafePrinterMixin):
    class TriggeredAlert(BaseModel):
        chat_id: str
        base_currency: str
        desired_currency: str
        threshold_percent: int
        old_rate: float
        old_rate_time: str
        new_rate: float
        new_rate_time: str
        price_change_percent: int

    class ActiveAlert(BaseModel):
        chat_id: str
        base_currency: str
        desired_currency: str
        threshold_percent: int
        last_price: float
        last_price_time: str

    __chat_config: ChatConfig
    __invoker: User

    __user_dao: UserCRUD
    __chat_config_dao: ChatConfigCRUD
    __price_alert_dao: PriceAlertCRUD
    __exchange_rate_fetcher: ExchangeRateFetcher

    def __init__(
        self,
        chat_id: str,
        invoker_user_id_hex: str,
        user_dao: UserCRUD,
        chat_config_dao: ChatConfigCRUD,
        price_alert_dao: PriceAlertCRUD,
        exchange_rate_fetcher: ExchangeRateFetcher,
    ):
        super().__init__(config.verbose)
        self.__user_dao = user_dao
        self.__chat_config_dao = chat_config_dao
        self.__price_alert_dao = price_alert_dao
        self.__exchange_rate_fetcher = exchange_rate_fetcher

        chat_config_db = self.__chat_config_dao.get(chat_id)
        if not chat_config_db:
            message = f"Chat '{chat_id}' not found"
            self.sprint(message)
            raise ValueError(message)
        self.__chat_config = ChatConfig.model_validate(chat_config_db)

        invoker_user_db = self.__user_dao.get(UUID(hex = invoker_user_id_hex))
        if not invoker_user_db:
            message = f"Invoker '{invoker_user_id_hex}' not found"
            self.sprint(message)
            raise ValueError(message)
        self.__invoker = User.model_validate(invoker_user_db)

    def create_alert(self, base_currency: str, desired_currency: str, threshold_percent: int) -> ActiveAlert:
        self.sprint(f"Setting price alert for {base_currency}/{desired_currency} at {threshold_percent}%")

        current_rate: float = self.__exchange_rate_fetcher.execute(base_currency, desired_currency)["rate"]
        price_alert_db = self.__price_alert_dao.save(
            PriceAlertSave(
                chat_id = self.__chat_config.chat_id,
                base_currency = base_currency,
                desired_currency = desired_currency,
                threshold_percent = threshold_percent,
                last_price = current_rate,
                last_price_time = datetime.now(),
            )
        )
        price_alert = PriceAlert.model_validate(price_alert_db)
        return PriceAlertManager.ActiveAlert(
            chat_id = price_alert.chat_id,
            base_currency = price_alert.base_currency,
            desired_currency = price_alert.desired_currency,
            threshold_percent = price_alert.threshold_percent,
            last_price = price_alert.last_price,
            last_price_time = price_alert.last_price_time.strftime(DATE_TIME_PRINT_FORMAT),
        )

    def get_all_alerts(self) -> list[ActiveAlert]:
        self.sprint(f"Listing price alerts for chat '{self.__chat_config.chat_id}'")
        price_alerts_db = self.__price_alert_dao.get_alerts_by_chat(self.__chat_config.chat_id)
        price_alerts = [PriceAlert.model_validate(alert) for alert in price_alerts_db]
        return [
            PriceAlertManager.ActiveAlert(
                chat_id = alert.chat_id,
                base_currency = alert.base_currency,
                desired_currency = alert.desired_currency,
                threshold_percent = alert.threshold_percent,
                last_price = alert.last_price,
                last_price_time = alert.last_price_time.strftime(DATE_TIME_PRINT_FORMAT),
            )
            for alert in price_alerts
        ]

    def delete_alert(self, base_currency: str, desired_currency: str) -> ActiveAlert | None:
        self.sprint(f"Deleting price alert for {base_currency}/{desired_currency}")
        deleted_alert_db = self.__price_alert_dao.delete(self.__chat_config.chat_id, base_currency, desired_currency)
        if deleted_alert_db:
            deleted_alert = PriceAlert.model_validate(deleted_alert_db)
            return PriceAlertManager.ActiveAlert(
                chat_id = deleted_alert.chat_id,
                base_currency = deleted_alert.base_currency,
                desired_currency = deleted_alert.desired_currency,
                threshold_percent = deleted_alert.threshold_percent,
                last_price = deleted_alert.last_price,
                last_price_time = deleted_alert.last_price_time.strftime(DATE_TIME_PRINT_FORMAT),
            )
        return None

    def check_alerts(self) -> list[TriggeredAlert]:
        self.sprint(f"Checking price alerts for chat '{self.__chat_config.chat_id}'")
        active_alerts = self.get_all_alerts()
        triggered_alerts: list[PriceAlertManager.TriggeredAlert] = []

        current_rate: float
        for alert in active_alerts:
            current_rate = self.__exchange_rate_fetcher.execute(alert.base_currency, alert.desired_currency)["rate"]
            price_change_percent: int
            if alert.last_price == 0:
                price_change_percent = int(math.ceil(current_rate * 100))
            else:
                change_ratio = (current_rate - alert.last_price) / alert.last_price
                price_change_percent = int(math.ceil(change_ratio * 100))

            if abs(price_change_percent) >= alert.threshold_percent:
                triggered_alerts.append(
                    PriceAlertManager.TriggeredAlert(
                        chat_id = alert.chat_id,
                        base_currency = alert.base_currency,
                        desired_currency = alert.desired_currency,
                        threshold_percent = alert.threshold_percent,
                        old_rate = alert.last_price,
                        old_rate_time = alert.last_price_time,
                        new_rate = current_rate,
                        new_rate_time = datetime.now().strftime(DATE_TIME_PRINT_FORMAT),
                        price_change_percent = price_change_percent,
                    )
                )
                self.__price_alert_dao.update(
                    PriceAlertSave(
                        chat_id = alert.chat_id,
                        base_currency = alert.base_currency,
                        desired_currency = alert.desired_currency,
                        threshold_percent = alert.threshold_percent,
                        last_price = current_rate,
                        last_price_time = datetime.now(),
                    )
                )
        return triggered_alerts
