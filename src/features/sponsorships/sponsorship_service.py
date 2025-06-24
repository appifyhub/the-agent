from datetime import datetime
from enum import Enum
from uuid import UUID

from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.model.user import UserDB
from db.schema.sponsorship import Sponsorship, SponsorshipSave
from db.schema.user import User, UserSave
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


class SponsorshipService(SafePrinterMixin):
    class Result(Enum):
        success = "success"
        failure = "failure"

    __user_dao: UserCRUD
    __sponsorship_dao: SponsorshipCRUD

    def __init__(
        self,
        user_dao: UserCRUD,
        sponsorship_dao: SponsorshipCRUD,
    ):
        super().__init__(config.verbose)
        self.__user_dao = user_dao
        self.__sponsorship_dao = sponsorship_dao

    def sponsor_user(self, sponsor_user_id_hex: str, receiver_telegram_username: str) -> tuple[Result, str]:
        self.sprint(f"Sponsor '{sponsor_user_id_hex}' is sponsoring receiver '@{receiver_telegram_username}'")

        # check if sponsor exists
        sponsor_user_db = self.__user_dao.get(UUID(hex = sponsor_user_id_hex))
        if not sponsor_user_db:
            message = f"Sponsor '{sponsor_user_id_hex}' not found"
            self.sprint(message)
            return SponsorshipService.Result.failure, message
        sponsor_user = User.model_validate(sponsor_user_db)

        # check if sponsor is sponsoring themselves
        if sponsor_user.telegram_username == receiver_telegram_username:
            message = f"Sponsor '@{receiver_telegram_username}' cannot sponsor themselves"
            self.sprint(message)
            return SponsorshipService.Result.failure, message

        # check if sponsor has exceeded the maximum number of sponsorships
        all_sponsor_sponsorships = self.__sponsorship_dao.get_all_by_sponsor(sponsor_user.id)
        is_sponsor_developer = sponsor_user.group == UserDB.Group.developer
        if len(all_sponsor_sponsorships) >= config.max_sponsorships_per_user and not is_sponsor_developer:
            message = f"Sponsor '{sponsor_user.id}' has exceeded the maximum number of sponsorships"
            self.sprint(message)
            return SponsorshipService.Result.failure, message

        # check if sponsor has any API key
        if not sponsor_user.has_any_api_key():
            message = f"Sponsor '{sponsor_user.id}' has no API keys configured"
            self.sprint(message)
            return SponsorshipService.Result.failure, message

        # check if sponsor is transitively sponsoring (sponsoring after being sponsored by someone else)
        all_sponsorships_received_by_sponsor = self.__sponsorship_dao.get_all_by_receiver(sponsor_user.id)
        if all_sponsorships_received_by_sponsor:
            message = f"Sponsor '{sponsor_user.id}' can't sponsor others before having a personal API key"
            self.sprint(message)
            return SponsorshipService.Result.failure, message

        # check if receiver already has a sponsorship
        receiver_user_db = self.__user_dao.get_by_telegram_username(receiver_telegram_username)
        receiver_user: User
        if receiver_user_db:
            receiver_user = User.model_validate(receiver_user_db)
            # check if receiver already has a sponsorship
            all_receiver_sponsorships = self.__sponsorship_dao.get_all_by_receiver(receiver_user.id)
            if all_receiver_sponsorships:
                message = f"Receiver '@{receiver_telegram_username}' already has a sponsorship"
                self.sprint(message)
                return SponsorshipService.Result.failure, message
            # check if receiver already has API keys - we don't want to override them
            if receiver_user.has_any_api_key():
                message = f"Receiver '@{receiver_telegram_username}' already has API keys configured"
                self.sprint(message)
                return SponsorshipService.Result.failure, message
            # receiver is eligible to be sponsored
            if receiver_user.telegram_chat_id:
                self.sprint(f"Receiver '@{receiver_telegram_username}' already has already messaged the bot")
                accepted_at = datetime.now()
            else:
                self.sprint(f"Receiver '@{receiver_telegram_username}' has not messaged the bot yet")
                accepted_at = None
            message = f"Activated! Send a welcome message to user '@{receiver_user.telegram_username}'"
        else:
            # create a new user for the receiver
            self.sprint(f"Creating new user for receiver '@{receiver_telegram_username}'")
            receiver_user_db = self.__user_dao.save(
                UserSave(
                    id = None,
                    full_name = None,
                    telegram_username = receiver_telegram_username,
                    telegram_chat_id = None,
                    telegram_user_id = None,
                    group = UserDB.Group.standard,
                ),
            )
            receiver_user = User.model_validate(receiver_user_db)
            accepted_at = None
            message = f"Sponsorship sent! Waiting for '{receiver_user.telegram_username}' to send the first message"

        # finally, create a sponsorship to track the relationship
        sponsorship_db = self.__sponsorship_dao.save(
            SponsorshipSave(
                sponsor_id = sponsor_user.id,
                receiver_id = receiver_user.id,
                accepted_at = accepted_at,
            ),
        )
        sponsorship = Sponsorship.model_validate(sponsorship_db)
        self.sprint(f"Sponsorship created from '{sponsorship.sponsor_id}' to '{sponsorship.receiver_id}'")
        return SponsorshipService.Result.success, message

    def unsponsor_user(self, sponsor_user_id_hex: str, receiver_telegram_username: str) -> tuple[Result, str]:
        self.sprint(f"Sponsor '{sponsor_user_id_hex}' is unsponsoring receiver '@{receiver_telegram_username}'")

        # check if sponsor exists
        sponsor_user_db = self.__user_dao.get(UUID(hex = sponsor_user_id_hex))
        if not sponsor_user_db:
            message = f"Sponsor '{sponsor_user_id_hex}' not found"
            self.sprint(message)
            return SponsorshipService.Result.failure, message
        sponsor_user = User.model_validate(sponsor_user_db)

        # check if receiver exists
        receiver_user_db = self.__user_dao.get_by_telegram_username(receiver_telegram_username)
        if not receiver_user_db:
            message = f"Receiver '@{receiver_telegram_username}' not found"
            self.sprint(message)
            return SponsorshipService.Result.failure, message
        receiver_user = User.model_validate(receiver_user_db)

        # check if sponsor has a sponsorship to receiver
        sponsorship_db = self.__sponsorship_dao.get(sponsor_user.id, receiver_user.id)
        if not sponsorship_db:
            message = f"Sponsor '{sponsor_user.id}' has no sponsorship to receiver '{receiver_user.id}'"
            self.sprint(message)
            return SponsorshipService.Result.failure, message
        sponsorship = Sponsorship.model_validate(sponsorship_db)

        # delete the sponsorship
        self.__sponsorship_dao.delete(sponsor_user.id, receiver_user.id)
        self.sprint(f"Sponsorship from '{sponsorship.sponsor_id}' to '{sponsorship.receiver_id}' deleted")

        message = f"Sponsorship revoked! Send a thanks/goodbye message to user '@{receiver_user.telegram_username}'"
        self.sprint(message)
        return SponsorshipService.Result.success, message

    def unsponsor_self(self, user_id_hex: str) -> tuple[Result, str]:
        self.sprint(f"User '{user_id_hex}' is unsponsoring themselves")

        # check if user exists
        user_db = self.__user_dao.get(UUID(hex = user_id_hex))
        if not user_db:
            message = f"User '{user_id_hex}' not found"
            self.sprint(message)
            return SponsorshipService.Result.failure, message
        user = User.model_validate(user_db)

        # check if user has any sponsorships as receiver
        sponsorships_db = self.__sponsorship_dao.get_all_by_receiver(user.id)
        if not sponsorships_db:
            message = f"User '{user.id}' has no sponsorships to remove"
            self.sprint(message)
            return SponsorshipService.Result.failure, message
        # assuming only one sponsorship per user
        sponsorship = Sponsorship.model_validate(sponsorships_db[0])

        # find the sponsor and call unsponsor_user
        if not user.telegram_username:
            message = f"User '{user.id}' has no telegram username"
            self.sprint(message)
            return SponsorshipService.Result.failure, message
        return self.unsponsor_user(sponsorship.sponsor_id.hex, user.telegram_username)

    def accept_sponsorship(self, receiver: User) -> bool:
        self.sprint(f"User '{receiver.id}' is trying to accept a sponsorship")

        # check if receiver already has API keys - don't accept sponsorship if they do
        if receiver.has_any_api_key():
            self.sprint(f"User '{receiver.id}' already has API keys configured, cannot accept sponsorship")
            return False

        # check if user has a sponsorship
        all_sponsorships = self.__sponsorship_dao.get_all_by_receiver(receiver.id)
        pending_sponsorships = [sponsorship for sponsorship in all_sponsorships if sponsorship.accepted_at is None]
        if not pending_sponsorships:
            self.sprint(f"User '{receiver.id}' has no pending sponsorships")
            return False

        # accept the sponsorship by updating its sponsorship_at timestamp
        sponsorship_db = pending_sponsorships[0]
        sponsorship = Sponsorship.model_validate(sponsorship_db)
        sponsorship_db = self.__sponsorship_dao.save(
            SponsorshipSave(
                sponsor_id = sponsorship.sponsor_id,
                receiver_id = sponsorship.receiver_id,
                accepted_at = datetime.now(),
            ),
        )
        sponsorship = Sponsorship.model_validate(sponsorship_db)
        self.sprint(f"Sponsorship from '{sponsorship.sponsor_id}' to '{sponsorship.receiver_id}' accepted")
        return True
