from datetime import datetime
from uuid import UUID, uuid4

from api.model.gumroad_ping_payload import GumroadPingPayload
from di.di import DI
from features.accounting.purchases.purchase_aggregates import PurchaseAggregates
from features.accounting.purchases.purchase_record import PurchaseRecord
from util import log


class PurchaseService:

    __di: DI

    def __init__(self, di: DI):
        self.__di = di

    def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        product_id: str | None = None,
    ) -> list[PurchaseRecord]:
        return self.__di.purchase_record_repo.get_by_user(
            user_id,
            skip = skip,
            limit = limit,
            start_date = start_date,
            end_date = end_date,
            product_id = product_id,
        )

    def get_aggregates_by_user(
        self,
        user_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        product_id: str | None = None,
    ) -> PurchaseAggregates:
        return self.__di.purchase_record_repo.get_aggregates_by_user(
            user_id,
            start_date = start_date,
            end_date = end_date,
            product_id = product_id,
        )

    def record_purchase(self, payload: GumroadPingPayload) -> PurchaseRecord:
        user_id: UUID | None = None
        if payload.url_params and "user_id" in payload.url_params:
            try:
                user_id_str = payload.url_params["user_id"]
                user_id = UUID(user_id_str)
                user = self.__di.user_crud.get(user_id)
                if user is None:
                    log.w(f"User {user_id_str} from url_params not found, storing without user_id")
                    user_id = None
            except (ValueError, KeyError) as e:
                log.w(f"Failed to parse user_id from url_params: {e}")
                user_id = None

        sale_timestamp = datetime.fromisoformat(payload.sale_timestamp.replace("Z", "+00:00"))

        record = PurchaseRecord(
            id = uuid4(),
            user_id = user_id,
            seller_id = payload.seller_id,
            sale_id = payload.sale_id,
            sale_timestamp = sale_timestamp,
            price = payload.price,
            product_id = payload.product_id,
            product_name = payload.product_name,
            product_permalink = payload.product_permalink,
            short_product_id = payload.short_product_id,
            license_key = payload.license_key,
            quantity = payload.quantity,
            gumroad_fee = payload.gumroad_fee,
            affiliate_credit_amount_cents = payload.affiliate_credit_amount_cents,
            discover_fee_charge = payload.discover_fee_charge,
            url_params = payload.url_params,
            custom_fields = payload.custom_fields,
            test = payload.test,
            is_preorder_authorization = payload.is_preorder_authorization,
            refunded = payload.refunded,
        )

        return self.__di.purchase_record_repo.save(record)

    def bind_license_key(self, user_id: UUID, license_key: str) -> PurchaseRecord:
        return self.__di.purchase_record_repo.bind_license_key_to_user(license_key, user_id)
