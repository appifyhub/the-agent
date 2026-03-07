from api.model.gumroad_ping_payload import GumroadPingPayload
from di.di import DI
from util import log
from util.config import config
from util.error_codes import UNAUTHORIZED_SELLER
from util.errors import AuthorizationError


class GumroadController:

    __di: DI

    def __init__(self, di: DI):
        self.__di = di

    def handle_ping(self, payload: GumroadPingPayload):
        log.t("Gumroad ping received", payload.model_dump())

        if config.gumroad_seller_id_check and payload.seller_id != config.gumroad_seller_id:
            raise AuthorizationError(f"Unauthorized seller ID: {payload.seller_id}", UNAUTHORIZED_SELLER)

        self.__di.purchase_service.record_purchase(payload)
