from api.model.gumroad_ping_payload import GumroadPingPayload
from di.di import DI
from util import log


class GumroadController:

    __di: DI

    def __init__(self, di: DI):
        self.__di = di

    def handle_ping(self, payload: GumroadPingPayload) -> None:
        log.i(f"Gumroad ping received: sale_id={payload.sale_id}, product={payload.product_name}, price={payload.price}")
        log.i("Full Gumroad payload", payload.model_dump())
