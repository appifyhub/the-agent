from datetime import datetime
from enum import Enum
from uuid import UUID

from db.crud.invite import InviteCRUD
from db.crud.user import UserCRUD
from db.model.user import UserDB
from db.schema.invite import InviteSave, Invite
from db.schema.user import User, UserSave
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


class InviteManager(SafePrinterMixin):
    class Result(Enum):
        success = "success"
        failure = "failure"

    __user_dao: UserCRUD
    __invite_dao: InviteCRUD

    def __init__(
        self,
        user_dao: UserCRUD,
        invite_dao: InviteCRUD,
    ):
        super().__init__(config.verbose)
        self.__user_dao = user_dao
        self.__invite_dao = invite_dao

    def invite_user(self, sender_user_id_hex: str, receiver_telegram_username: str) -> tuple[Result, str]:
        self.sprint(f"Sender '{sender_user_id_hex}' is inviting receiver '@{receiver_telegram_username}'")

        # check if sender exists
        sender_user_db = self.__user_dao.get(UUID(hex = sender_user_id_hex))
        if not sender_user_db:
            message = f"Sender '{sender_user_id_hex}' not found"
            self.sprint(message)
            return InviteManager.Result.failure, message
        sender_user = User.model_validate(sender_user_db)

        # check if sender is inviting themselves
        if sender_user.telegram_username == receiver_telegram_username:
            message = f"Sender '@{receiver_telegram_username}' cannot invite themselves"
            self.sprint(message)
            return InviteManager.Result.failure, message

        # check if sender has exceeded the maximum number of invites
        all_sender_invites = self.__invite_dao.get_all_by_sender(sender_user.id)
        is_sender_developer = sender_user.group == UserDB.Group.developer
        if len(all_sender_invites) >= config.max_invites_per_user and not is_sender_developer:
            message = f"Sender '{sender_user.id}' has exceeded the maximum number of invites"
            self.sprint(message)
            return InviteManager.Result.failure, message

        # check if sender has a valid API key
        if not sender_user.open_ai_key:
            message = f"Sender '{sender_user.id}' has no valid API key set up"
            self.sprint(message)
            return InviteManager.Result.failure, message

        # check if sender is transitively inviting (inviting after being invited by someone else)
        all_invites_received_by_sender = self.__invite_dao.get_all_by_receiver(sender_user.id)
        if all_invites_received_by_sender:
            message = f"Sender '{sender_user.id}' can't invite others until they start using their own API key"
            self.sprint(message)
            return InviteManager.Result.failure, message

        # check if receiver already has an invitation or an API key
        receiver_user_db = self.__user_dao.get_by_telegram_username(receiver_telegram_username)
        if receiver_user_db:
            receiver_user = User.model_validate(receiver_user_db)
            all_receiver_invites = self.__invite_dao.get_all_by_receiver(receiver_user.id)
            if all_receiver_invites:
                message = f"Receiver '@{receiver_telegram_username}' already has an invitation"
                self.sprint(message)
                return InviteManager.Result.failure, message
            if receiver_user.open_ai_key:
                message = f"Receiver '@{receiver_telegram_username}' already has an API key set up"
                self.sprint(message)
                return InviteManager.Result.failure, message
            # update receiver to use sender's API key
            self.sprint(f"Updating receiver '@{receiver_telegram_username}' to use sender's API key")
            receiver_user_db = self.__user_dao.save(
                UserSave(
                    id = receiver_user.id,
                    full_name = receiver_user.full_name,
                    telegram_username = receiver_user.telegram_username,
                    telegram_chat_id = receiver_user.telegram_chat_id,
                    telegram_user_id = receiver_user.telegram_user_id,
                    open_ai_key = sender_user.open_ai_key,
                    group = receiver_user.group,
                )
            )
            receiver_user = User.model_validate(receiver_user_db)
            accepted_at = datetime.now()
            message = f"Activated! Send a welcome message to user '@{receiver_user.telegram_username}'"
        else:
            # create a new user for the receiver persona with the sender's API key
            self.sprint(f"Creating new user for receiver '@{receiver_telegram_username}'")
            receiver_user_db = self.__user_dao.save(
                UserSave(
                    id = None,
                    full_name = None,
                    telegram_username = receiver_telegram_username,
                    telegram_chat_id = None,
                    telegram_user_id = None,
                    open_ai_key = sender_user.open_ai_key,
                    group = UserDB.Group.standard,
                )
            )
            receiver_user = User.model_validate(receiver_user_db)
            accepted_at = None
            message = f"Invite sent! Waiting for '{receiver_user.telegram_username}' to send a message to the bot"

        # finally, create an invitation to track the relationship
        invite_db = self.__invite_dao.save(
            InviteSave(
                sender_id = sender_user.id,
                receiver_id = receiver_user.id,
                accepted_at = accepted_at,
            )
        )
        invite = Invite.model_validate(invite_db)
        self.sprint(f"Invite created from '{invite.sender_id}' to '{invite.receiver_id}'")
        return InviteManager.Result.success, message

    def uninvite_user(self, sender_user_id_hex: str, receiver_telegram_username: str) -> tuple[Result, str]:
        self.sprint(f"Sender '{sender_user_id_hex}' is uninviting receiver '@{receiver_telegram_username}'")

        # check if sender exists
        sender_user_db = self.__user_dao.get(UUID(hex = sender_user_id_hex))
        if not sender_user_db:
            message = f"Sender '{sender_user_id_hex}' not found"
            self.sprint(message)
            return InviteManager.Result.failure, message
        sender_user = User.model_validate(sender_user_db)

        # check if sender has a valid API key
        if not sender_user.open_ai_key:
            message = f"Sender '{sender_user.id}' has no valid API key set up"
            self.sprint(message)
            return InviteManager.Result.failure, message

        # check if receiver exists
        receiver_user_db = self.__user_dao.get_by_telegram_username(receiver_telegram_username)
        if not receiver_user_db:
            message = f"Receiver '@{receiver_telegram_username}' not found"
            self.sprint(message)
            return InviteManager.Result.failure, message
        receiver_user = User.model_validate(receiver_user_db)

        # check if sender has an invitation to receiver
        invite_db = self.__invite_dao.get(sender_user.id, receiver_user.id)
        if not invite_db:
            message = f"Sender '{sender_user.id}' has no invitation to receiver '{receiver_user.id}'"
            self.sprint(message)
            return InviteManager.Result.failure, message
        invite = Invite.model_validate(invite_db)

        # delete the invitation
        self.__invite_dao.delete(sender_user.id, receiver_user.id)
        self.sprint(f"Invite from '{invite.sender_id}' to '{invite.receiver_id}' deleted")

        # check if receiver's API key needs to be revoked
        message_appendix = " API key was not shared."
        if sender_user.open_ai_key == receiver_user.open_ai_key:
            self.sprint(f"Removing API key for receiver '@{receiver_telegram_username}'")
            self.__user_dao.save(
                UserSave(
                    id = receiver_user.id,
                    full_name = receiver_user.full_name,
                    telegram_username = receiver_user.telegram_username,
                    telegram_chat_id = receiver_user.telegram_chat_id,
                    telegram_user_id = receiver_user.telegram_user_id,
                    open_ai_key = None,
                    group = receiver_user.group,
                )
            )
            message_appendix = (
                " Shared API key was also removed from the receiver."
                f" Send a thanks/goodbye message to user '@{receiver_user.telegram_username}'"
            )
        message = f"Invite revoked!{message_appendix}"
        self.sprint(message)
        return InviteManager.Result.success, message

    def accept_invite(self, receiver: User) -> bool:
        self.sprint(f"User '{receiver.id}' is trying to accept an invitation")

        # check if user has a valid API key
        if not receiver.open_ai_key:
            self.sprint(f"User '{receiver.id}' has no valid API key set up")
            return False

        # check if user has an invitation
        all_invites = self.__invite_dao.get_all_by_receiver(receiver.id)
        pending_invites = [invite for invite in all_invites if invite.accepted_at is None]
        if not pending_invites:
            self.sprint(f"User '{receiver.id}' has no pending invitations")
            return False

        # accept the invitation by updating its accepted_at timestamp
        invite_db = pending_invites[0]
        invite = Invite.model_validate(invite_db)
        invite_db = self.__invite_dao.save(
            InviteSave(
                sender_id = invite.sender_id,
                receiver_id = invite.receiver_id,
                accepted_at = datetime.now(),
            )
        )
        invite = Invite.model_validate(invite_db)
        self.sprint(f"Invite from '{invite.sender_id}' to '{invite.receiver_id}' accepted")
        return True

    def purge_accepted_invites(self, receiver: User) -> int:
        self.sprint(f"Purging accepted invites for user '{receiver.id}'")
        deleted_count = self.__invite_dao.delete_all_by_receiver(receiver.id)
        self.sprint(f"Deleted {deleted_count} accepted invites for '{receiver.id}'")
        return deleted_count
