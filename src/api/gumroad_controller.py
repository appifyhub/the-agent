from api.model.gumroad_ping_payload import GumroadPingPayload
from di.di import DI
from features.accounting.purchases.purchase_record import PurchaseRecord
from util import log
from util.config import config


class GumroadController:

    __di: DI

    def __init__(self, di: DI):
        self.__di = di

    def handle_ping(self, payload: GumroadPingPayload) -> PurchaseRecord:
        log.t("Gumroad ping received", payload.model_dump())

        if config.gumroad_seller_id_check and payload.seller_id != config.gumroad_seller_id:
            raise ValueError(f"Unauthorized seller ID: {payload.seller_id}")

        return self.__di.purchase_service.record_purchase(payload)
