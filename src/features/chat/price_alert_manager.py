import math
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from api.authorization_service import AuthorizationService
from db.crud.chat_config import ChatConfigCRUD
from db.crud.price_alert import PriceAlertCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.tools_cache import ToolsCacheCRUD
from db.crud.user import UserCRUD
from db.model.price_alert import PriceAlertDB
from db.schema.chat_config import ChatConfig
from db.schema.price_alert import PriceAlert, PriceAlertSave
from db.schema.user import User
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.currencies.exchange_rate_fetcher import ExchangeRateFetcher
from features.prompting.prompt_library import TELEGRAM_BOT_USER
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin, sprint

DATETIME_PRINT_FORMAT = "%Y-%m-%d %H:%M %Z"


class PriceAlertManager(SafePrinterMixin):
    class TriggeredAlert(BaseModel):
        chat_id: str
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
        chat_id: str
        owner_id: UUID
        base_currency: str
        desired_currency: str
        threshold_percent: int
        last_price: float
        last_price_time: str

    __target_chat_config: ChatConfig | None
    __invoker_user: User
    __user_dao: UserCRUD
    __chat_config_dao: ChatConfigCRUD
    __price_alert_dao: PriceAlertCRUD
    __tools_cache_dao: ToolsCacheCRUD
    __sponsorship_dao: SponsorshipCRUD
    __telegram_bot_sdk: TelegramBotSDK

    def __init__(
        self,
        target_chat_id: str | None,  # can be all chats or a specific chat
        invoker_user_id_hex: str,
        user_dao: UserCRUD,
        chat_config_dao: ChatConfigCRUD,
        price_alert_dao: PriceAlertCRUD,
        tools_cache_dao: ToolsCacheCRUD,
        sponsorship_dao: SponsorshipCRUD,
        telegram_bot_sdk: TelegramBotSDK,
    ):
        super().__init__(config.verbose)
        self.__user_dao = user_dao
        self.__chat_config_dao = chat_config_dao
        self.__price_alert_dao = price_alert_dao
        self.__tools_cache_dao = tools_cache_dao
        self.__sponsorship_dao = sponsorship_dao
        self.__telegram_bot_sdk = telegram_bot_sdk
        authorization_service = AuthorizationService(telegram_bot_sdk, user_dao, chat_config_dao)
        self.__invoker_user = authorization_service.validate_user(invoker_user_id_hex)
        self.__target_chat_config = authorization_service.validate_chat(target_chat_id) if target_chat_id else None

    def create_alert(self, base_currency: str, desired_currency: str, threshold_percent: int) -> ActiveAlert:
        self.sprint(f"Setting price alert for {base_currency}/{desired_currency} at {threshold_percent}%")
        if not self.__target_chat_config:
            message = "Target chat is not set"
            self.sprint(message)
            raise ValueError(message)
        if self.__invoker_user.id == TELEGRAM_BOT_USER.id:
            message = "Bot cannot set price alerts"
            self.sprint(message)
            raise ValueError(message)

        exchange_rate_fetcher = ExchangeRateFetcher(
            self.__invoker_user,
            self.__user_dao,
            self.__chat_config_dao,
            self.__tools_cache_dao,
            self.__sponsorship_dao,
            self.__telegram_bot_sdk,
        )
        current_rate: float = exchange_rate_fetcher.execute(base_currency, desired_currency)["rate"]
        price_alert_db = self.__price_alert_dao.save(
            PriceAlertSave(
                chat_id = self.__target_chat_config.chat_id,
                owner_id = self.__invoker_user.id,
                base_currency = base_currency,
                desired_currency = desired_currency,
                threshold_percent = threshold_percent,
                last_price = current_rate,
                last_price_time = datetime.now(),
            ),
        )
        price_alert = PriceAlert.model_validate(price_alert_db)
        return PriceAlertManager.ActiveAlert(
            chat_id = price_alert.chat_id,
            owner_id = price_alert.owner_id,
            base_currency = price_alert.base_currency,
            desired_currency = price_alert.desired_currency,
            threshold_percent = price_alert.threshold_percent,
            last_price = price_alert.last_price,
            last_price_time = price_alert.last_price_time.strftime(DATETIME_PRINT_FORMAT),
        )

    def delete_alert(self, base_currency: str, desired_currency: str) -> ActiveAlert | None:
        self.sprint(f"Deleting price alert for {base_currency}/{desired_currency}")
        if not self.__target_chat_config:
            message = "Target chat is not set"
            self.sprint(message)
            raise ValueError(message)

        deleted_alert_db = self.__price_alert_dao.delete(
            self.__target_chat_config.chat_id, base_currency, desired_currency,
        )
        if deleted_alert_db:
            deleted_alert = PriceAlert.model_validate(deleted_alert_db)
            return PriceAlertManager.ActiveAlert(
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
            sprint(f"Listing price alerts for chat '{self.__target_chat_config.chat_id}'")
            price_alerts_db = self.__price_alert_dao.get_alerts_by_chat(self.__target_chat_config.chat_id)
        else:
            sprint("Listing all price alerts")
            price_alerts_db = self.__price_alert_dao.get_all()
        price_alerts = [PriceAlert.model_validate(price_alert_db) for price_alert_db in price_alerts_db]
        return [
            PriceAlertManager.ActiveAlert(
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
        sprint("Checking triggered price alerts")

        active_alerts = self.get_active_alerts()
        triggered_alerts: list[PriceAlertManager.TriggeredAlert] = []
        for alert in active_alerts:
            try:
                exchange_rate_fetcher = ExchangeRateFetcher(
                    alert.owner_id,
                    self.__user_dao,
                    self.__chat_config_dao,
                    self.__tools_cache_dao,
                    self.__sponsorship_dao,
                    self.__telegram_bot_sdk,
                )
                current_rate: float = exchange_rate_fetcher.execute(alert.base_currency, alert.desired_currency)["rate"]
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
                    self.__price_alert_dao.update(
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
                self.sprint(f"Failed to check chat '{alert.chat_id}' alert '{currency_pair}'", e)
                continue
        return triggered_alerts
