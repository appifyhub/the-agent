from api.model.credit_transfer_payload import CreditTransferPayload
from db.model.chat_config import ChatConfigDB
from di.di import DI
from util import log
from util.error_codes import INVALID_PLATFORM
from util.errors import ValidationError


class TransfersController:

    __di: DI

    def __init__(self, di: DI):
        self.__di = di

    def transfer_credits(self, sender_user_id_hex: str, payload: CreditTransferPayload) -> None:
        user = self.__di.authorization_service.authorize_for_user(self.__di.invoker, sender_user_id_hex)
        log.d(f"Transferring {payload.amount} credits to {payload.platform}/'@{payload.platform_handle}'")

        chat_type = ChatConfigDB.ChatType.lookup(payload.platform)
        if not chat_type:
            raise ValidationError(f"Unsupported platform: {payload.platform}", INVALID_PLATFORM)

        self.__di.credit_transfer_service.transfer_credits(
            sender_id = user.id,
            recipient_handle = payload.platform_handle,
            chat_type = chat_type,
            amount = payload.amount,
            note = payload.note,
        )

        log.i(f"Transfer completed: {payload.amount} credits to '@{payload.platform_handle}'")
