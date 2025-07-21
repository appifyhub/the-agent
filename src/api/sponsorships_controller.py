from typing import Any

from db.model.user import UserDB
from db.schema.sponsorship import Sponsorship
from db.schema.user import User
from di.di import DI
from features.sponsorships.sponsorship_service import SponsorshipService
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


class SponsorshipsController(SafePrinterMixin):
    __di: DI

    def __init__(self, di: DI):
        super().__init__(config.verbose)
        self.__di = di

    def fetch_sponsorships(self, user_id_hex: str) -> dict[str, Any]:
        self.sprint(f"Fetching sponsorships for user '{user_id_hex}'")
        user = self.__di.authorization_service.authorize_for_user(self.__di.invoker, user_id_hex)
        sponsorships_db = self.__di.sponsorship_crud.get_all_by_sponsor(user.id)
        max_sponsorships = (
            config.max_sponsorships_per_user
            if self.__di.invoker.group != UserDB.Group.developer
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
            receiver_user_db = self.__di.user_crud.get(sponsorship.receiver_id)
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
        user = self.__di.authorization_service.authorize_for_user(self.__di.invoker, sponsor_user_id_hex)
        self.sprint(f"Sponsoring user '@{receiver_telegram_username}' by '{self.__di.invoker.id.hex}'")
        result, message = self.__di.sponsorship_service.sponsor_user(
            sponsor_user_id_hex = user.id.hex,
            receiver_telegram_username = receiver_telegram_username,
        )
        if result == SponsorshipService.Result.failure:
            raise ValueError(message)
        self.sprint(f"  Successfully sponsored '@{receiver_telegram_username}'")

    def unsponsor_user(self, sponsor_user_id_hex: str, receiver_telegram_username: str):
        user = self.__di.authorization_service.authorize_for_user(self.__di.invoker, sponsor_user_id_hex)
        self.sprint(f"Unsponsoring user '@{receiver_telegram_username}' by '{self.__di.invoker.id.hex}'")
        result, message = self.__di.sponsorship_service.unsponsor_user(
            sponsor_user_id_hex = user.id.hex,
            receiver_telegram_username = receiver_telegram_username,
        )
        if result == SponsorshipService.Result.failure:
            raise ValueError(message)
        self.sprint(f"  Successfully unsponsored '@{receiver_telegram_username}'")

    def unsponsor_self(self, user_id_hex: str):
        user = self.__di.authorization_service.authorize_for_user(self.__di.invoker, user_id_hex)
        self.sprint(f"User '{user.id.hex}' is unsponsoring themselves")
        result, message = self.__di.sponsorship_service.unsponsor_self(user.id.hex)
        if result == SponsorshipService.Result.failure:
            raise ValueError(message)
        self.sprint("  Successfully unsponsored self")
