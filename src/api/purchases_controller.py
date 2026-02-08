from datetime import datetime

from di.di import DI
from features.accounting.purchases.purchase_aggregates import PurchaseAggregates
from features.accounting.purchases.purchase_record import PurchaseRecord
from util import log


class PurchasesController:

    __di: DI

    def __init__(self, di: DI):
        self.__di = di

    def fetch_purchase_records(
        self,
        user_id_hex: str,
        skip: int = 0,
        limit: int = 50,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        product_id: str | None = None,
    ) -> list[PurchaseRecord]:
        if limit > 100:
            raise ValueError("limit cannot exceed 100")
        log.d(f"Fetching purchase records for user '{user_id_hex}'")
        user = self.__di.authorization_service.authorize_for_user(self.__di.invoker, user_id_hex)
        return self.__di.purchase_service.get_by_user(
            user.id,
            skip = skip,
            limit = limit,
            start_date = start_date,
            end_date = end_date,
            product_id = product_id,
        )

    def fetch_purchase_aggregates(
        self,
        user_id_hex: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        product_id: str | None = None,
    ) -> PurchaseAggregates:
        log.d(f"Fetching purchase aggregates for user '{user_id_hex}'")
        user = self.__di.authorization_service.authorize_for_user(self.__di.invoker, user_id_hex)
        return self.__di.purchase_service.get_aggregates_by_user(
            user.id,
            start_date = start_date,
            end_date = end_date,
            product_id = product_id,
        )

    def bind_license_key(
        self,
        user_id_hex: str,
        license_key: str,
    ) -> PurchaseRecord:
        log.d(f"Binding license key for user '{user_id_hex}'")
        user = self.__di.authorization_service.authorize_for_user(self.__di.invoker, user_id_hex)
        return self.__di.purchase_service.bind_license_key(user.id, license_key)
