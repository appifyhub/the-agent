import math
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from db.model.chat_config import ChatConfigDB
from db.model.price_alert import PriceAlertDB
from db.schema.chat_config import ChatConfig
from db.schema.price_alert import PriceAlert, PriceAlertSave
from di.di import DI
from features.integrations.integrations import resolve_agent_user
from util import log

DATETIME_PRINT_FORMAT = "%Y-%m-%d %H:%M %Z"


class CurrencyAlertService:

    class TriggeredAlert(BaseModel):
        chat_id: UUID
        owner_id: UUID
        base_currency: str
        desired_currency: str
        threshold_percent: int
        old_rate: float
        old_rate_time: str
        new_rate: float
        new_rate_time: str
        price_change_percent: int

    class ActiveAlert(BaseModel):
        chat_id: UUID
        owner_id: UUID
        base_currency: str
        desired_currency: str
        threshold_percent: int
        last_price: float
        last_price_time: str

    __target_chat_config: ChatConfig | None
    __di: DI

    def __init__(
        self,
        target_chat_id: str | None,  # can be for a specific chat, or all chats
        di: DI,
    ):
        self.__di = di
        self.__target_chat_config = self.__di.authorization_service.validate_chat(target_chat_id) if target_chat_id else None

    def create_alert(self, base_currency: str, desired_currency: str, threshold_percent: int) -> ActiveAlert:
        log.d(f"Setting price alert for {base_currency}/{desired_currency} at {threshold_percent}%")
        if not self.__target_chat_config:
            raise ValueError(log.e("Target chat is not set"))
        agent_user = resolve_agent_user(ChatConfigDB.ChatType.background)
        if self.__di.invoker.id == agent_user.id:
            raise ValueError(log.e("Bot cannot set price alerts"))

        current_rate: float = self.__di.exchange_rate_fetcher.execute(base_currency, desired_currency)["rate"]
        price_alert_db = self.__di.price_alert_crud.save(
            PriceAlertSave(
                chat_id = self.__target_chat_config.chat_id,
                owner_id = self.__di.invoker.id,
                base_currency = base_currency,
                desired_currency = desired_currency,
                threshold_percent = threshold_percent,
                last_price = current_rate,
                last_price_time = datetime.now(),
            ),
        )
        price_alert = PriceAlert.model_validate(price_alert_db)
        return CurrencyAlertService.ActiveAlert(
            chat_id = price_alert.chat_id,
            owner_id = price_alert.owner_id,
            base_currency = price_alert.base_currency,
            desired_currency = price_alert.desired_currency,
            threshold_percent = price_alert.threshold_percent,
            last_price = price_alert.last_price,
            last_price_time = price_alert.last_price_time.strftime(DATETIME_PRINT_FORMAT),
        )

    def delete_alert(self, base_currency: str, desired_currency: str) -> ActiveAlert | None:
        log.d(f"Deleting price alert for {base_currency}/{desired_currency}")
        if not self.__target_chat_config:
            raise ValueError(log.e("Target chat is not set"))

        deleted_alert_db = self.__di.price_alert_crud.delete(
            self.__target_chat_config.chat_id, base_currency, desired_currency,
        )
        if deleted_alert_db:
            deleted_alert = PriceAlert.model_validate(deleted_alert_db)
            return CurrencyAlertService.ActiveAlert(
                chat_id = deleted_alert.chat_id,
                owner_id = deleted_alert.owner_id,
                base_currency = deleted_alert.base_currency,
                desired_currency = deleted_alert.desired_currency,
                threshold_percent = deleted_alert.threshold_percent,
                last_price = deleted_alert.last_price,
                last_price_time = deleted_alert.last_price_time.strftime(DATETIME_PRINT_FORMAT),
            )
        return None

    def get_active_alerts(self) -> list[ActiveAlert]:
        price_alerts_db: list[PriceAlertDB]
        if self.__target_chat_config:
            log.d(f"Listing price alerts for chat '{self.__target_chat_config.chat_id}'")
            price_alerts_db = self.__di.price_alert_crud.get_alerts_by_chat(self.__target_chat_config.chat_id)
        else:
            log.d("Listing all price alerts")
            price_alerts_db = self.__di.price_alert_crud.get_all()
        price_alerts = [PriceAlert.model_validate(price_alert_db) for price_alert_db in price_alerts_db]
        return [
            CurrencyAlertService.ActiveAlert(
                chat_id = price_alert.chat_id,
                owner_id = price_alert.owner_id,
                base_currency = price_alert.base_currency,
                desired_currency = price_alert.desired_currency,
                threshold_percent = price_alert.threshold_percent,
                last_price = price_alert.last_price,
                last_price_time = price_alert.last_price_time.strftime(DATETIME_PRINT_FORMAT),
            )
            for price_alert in price_alerts
        ]

    def get_triggered_alerts(self) -> list[TriggeredAlert]:
        log.d("Checking triggered price alerts")

        active_alerts = self.get_active_alerts()
        triggered_alerts: list[CurrencyAlertService.TriggeredAlert] = []
        for alert in active_alerts:
            try:
                scoped_di = self.__di.clone(invoker_id = alert.owner_id.hex, invoker_chat_id = alert.chat_id.hex)
                current_rate: float = scoped_di.exchange_rate_fetcher.execute(alert.base_currency, alert.desired_currency)["rate"]
                price_change_percent: int
                if alert.last_price == 0:
                    price_change_percent = int(math.ceil(current_rate * 100))
                else:
                    change_ratio = (current_rate - alert.last_price) / alert.last_price
                    price_change_percent = int(math.ceil(change_ratio * 100))

                if abs(price_change_percent) >= alert.threshold_percent:
                    triggered_alerts.append(
                        CurrencyAlertService.TriggeredAlert(
                            chat_id = alert.chat_id,
                            owner_id = alert.owner_id,
                            base_currency = alert.base_currency,
                            desired_currency = alert.desired_currency,
                            threshold_percent = alert.threshold_percent,
                            old_rate = alert.last_price,
                            old_rate_time = alert.last_price_time,
                            new_rate = current_rate,
                            new_rate_time = datetime.now().strftime(DATETIME_PRINT_FORMAT),
                            price_change_percent = price_change_percent,
                        ),
                    )
                    self.__di.price_alert_crud.update(
                        PriceAlertSave(
                            chat_id = alert.chat_id,
                            owner_id = alert.owner_id,
                            base_currency = alert.base_currency,
                            desired_currency = alert.desired_currency,
                            threshold_percent = alert.threshold_percent,
                            last_price = current_rate,
                            last_price_time = datetime.now(),
                        ),
                    )
            except Exception as e:
                currency_pair = f"{alert.base_currency}/{alert.desired_currency}"
                log.w(f"Failed to check chat '{alert.chat_id}' alert '{currency_pair}'", e)
                continue
        return triggered_alerts
