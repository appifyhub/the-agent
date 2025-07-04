from typing import Any

from api.authorization_service import AuthorizationService
from db.crud.chat_config import ChatConfigCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.model.user import UserDB
from db.schema.sponsorship import Sponsorship
from db.schema.user import User
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.sponsorships.sponsorship_service import SponsorshipService
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


class SponsorshipsController(SafePrinterMixin):
    __invoker_user: User
    __authorization_service: AuthorizationService
    __sponsorship_service: SponsorshipService
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
        self.__sponsorship_service = SponsorshipService(user_dao, sponsorship_dao)
        self.__user_dao = user_dao
        self.__sponsorship_dao = sponsorship_dao
        self.__invoker_user = self.__authorization_service.validate_user(invoker_user_id_hex)

    def fetch_sponsorships(self, user_id_hex: str) -> dict[str, Any]:
        self.sprint(f"Fetching sponsorships for user '{user_id_hex}'")
        user = self.__authorization_service.authorize_for_user(self.__invoker_user, user_id_hex)
        sponsorships_db = self.__sponsorship_dao.get_all_by_sponsor(user.id)
        max_sponsorships = (
            config.max_sponsorships_per_user
            if self.__invoker_user.group != UserDB.Group.developer
            else config.max_users
        )
        if not sponsorships_db:
            self.sprint("  No sponsorships found")
            return {
                "sponsorships": [],
                "max_sponsorships": max_sponsorships,
            }

        sponsorships = [Sponsorship.model_validate(sponsorship_db) for sponsorship_db in sponsorships_db]
        output_sponsorships: list[dict[str, Any]] = []
        for sponsorship in sponsorships:
            receiver_user_db = self.__user_dao.get(sponsorship.receiver_id)
            if not receiver_user_db:
                self.sprint(f"  Receiver user with id {sponsorship.receiver_id} not found, skipping.")
                continue
            receiver_user = User.model_validate(receiver_user_db)
            output_sponsorships.append(
                {
                    "full_name": receiver_user.full_name,
                    "telegram_username": receiver_user.telegram_username,
                    "sponsored_at": sponsorship.sponsored_at.isoformat(),
                    "accepted_at": sponsorship.accepted_at.isoformat() if sponsorship.accepted_at else None,
                },
            )
        return {
            "sponsorships": output_sponsorships,
            "max_sponsorships": max_sponsorships,
        }

    def sponsor_user(self, sponsor_user_id_hex: str, receiver_telegram_username: str):
        user = self.__authorization_service.authorize_for_user(self.__invoker_user, sponsor_user_id_hex)
        self.sprint(f"Sponsoring user '@{receiver_telegram_username}' by '{self.__invoker_user.id.hex}'")
        result, message = self.__sponsorship_service.sponsor_user(
            sponsor_user_id_hex = user.id.hex,
            receiver_telegram_username = receiver_telegram_username,
        )
        if result == SponsorshipService.Result.failure:
            raise ValueError(message)
        self.sprint(f"  Successfully sponsored '@{receiver_telegram_username}'")

    def unsponsor_user(self, sponsor_user_id_hex: str, receiver_telegram_username: str):
        user = self.__authorization_service.authorize_for_user(self.__invoker_user, sponsor_user_id_hex)
        self.sprint(f"Unsponsoring user '@{receiver_telegram_username}' by '{self.__invoker_user.id.hex}'")
        result, message = self.__sponsorship_service.unsponsor_user(
            sponsor_user_id_hex = user.id.hex,
            receiver_telegram_username = receiver_telegram_username,
        )
        if result == SponsorshipService.Result.failure:
            raise ValueError(message)
        self.sprint(f"  Successfully unsponsored '@{receiver_telegram_username}'")

    def unsponsor_self(self, user_id_hex: str):
        user = self.__authorization_service.authorize_for_user(self.__invoker_user, user_id_hex)
        self.sprint(f"User '{user.id.hex}' is unsponsoring themselves")
        result, message = self.__sponsorship_service.unsponsor_self(user.id.hex)
        if result == SponsorshipService.Result.failure:
            raise ValueError(message)
        self.sprint("  Successfully unsponsored self")
