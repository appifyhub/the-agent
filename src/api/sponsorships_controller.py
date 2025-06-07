from typing import Any

from api.authorization_service import AuthorizationService
from db.crud.chat_config import ChatConfigCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.schema.sponsorship import Sponsorship
from db.schema.user import User
from features.chat.sponsorship_manager import SponsorshipManager
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


class SponsorshipsController(SafePrinterMixin):
    invoker_user: User

    __authorization_service: AuthorizationService
    __sponsorship_manager: SponsorshipManager
    __user_dao: UserCRUD
    __sponsorship_dao: SponsorshipCRUD

    def __init__(
        self,
        invoker_user_id_hex: str,
        user_dao: UserCRUD,
        sponsorship_dao: SponsorshipCRUD,
        telegram_sdk: TelegramBotSDK,
        chat_config_dao: ChatConfigCRUD,
    ):
        super().__init__(config.verbose)
        self.__authorization_service = AuthorizationService(telegram_sdk, user_dao, chat_config_dao)
        self.__sponsorship_manager = SponsorshipManager(user_dao, sponsorship_dao)
        self.__user_dao = user_dao
        self.__sponsorship_dao = sponsorship_dao
        self.invoker_user = self.__authorization_service.validate_user(invoker_user_id_hex)

    def fetch_sponsorships(self, user_id_hex: str) -> list[dict[str, Any]]:
        self.sprint(f"Fetching sponsorships for user '{user_id_hex}'")
        user = self.__authorization_service.authorize_for_user(self.invoker_user, user_id_hex)
        sponsorships_db = self.__sponsorship_dao.get_all_by_sponsor(user.id)
        if not sponsorships_db:
            self.sprint("  No sponsorships found")
            return []

        sponsorships = [Sponsorship.model_validate(sponsorship_db) for sponsorship_db in sponsorships_db]
        result: list[dict[str, Any]] = []
        for sponsorship in sponsorships:
            receiver_user_db = self.__user_dao.get(sponsorship.receiver_id)
            if not receiver_user_db:
                self.sprint(f"  Receiver user with id {sponsorship.receiver_id} not found, skipping.")
                continue
            receiver_user = User.model_validate(receiver_user_db)
            result.append(
                {
                    "full_name": receiver_user.full_name,
                    "telegram_username": receiver_user.telegram_username,
                    "sponsored_at": sponsorship.sponsored_at.isoformat(),
                    "accepted_at": sponsorship.accepted_at.isoformat() if sponsorship.accepted_at else None,
                }
            )
        return result

    def sponsor_user(self, sponsor_user_id_hex: str, receiver_telegram_username: str):
        user = self.__authorization_service.authorize_for_user(self.invoker_user, sponsor_user_id_hex)
        self.sprint(f"Sponsoring user '@{receiver_telegram_username}' by '{self.invoker_user.id.hex}'")
        result, message = self.__sponsorship_manager.sponsor_user(
            sponsor_user_id_hex = user.id.hex,
            receiver_telegram_username = receiver_telegram_username,
        )
        if result == SponsorshipManager.Result.failure:
            raise ValueError(message)
        self.sprint(f"  Successfully sponsored '@{receiver_telegram_username}'")

    def unsponsor_user(self, sponsor_user_id_hex: str, receiver_telegram_username: str):
        user = self.__authorization_service.authorize_for_user(self.invoker_user, sponsor_user_id_hex)
        self.sprint(f"Unsponsoring user '@{receiver_telegram_username}' by '{self.invoker_user.id.hex}'")
        result, message = self.__sponsorship_manager.unsponsor_user(
            sponsor_user_id_hex = user.id.hex,
            receiver_telegram_username = receiver_telegram_username,
        )
        if result == SponsorshipManager.Result.failure:
            raise ValueError(message)
        self.sprint(f"  Successfully unsponsored '@{receiver_telegram_username}'")
