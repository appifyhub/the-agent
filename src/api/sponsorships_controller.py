from typing import Any

from api.model.sponsorship_payload import SponsorshipPayload
from db.model.chat_config import ChatConfigDB
from db.model.user import UserDB
from db.schema.sponsorship import Sponsorship
from db.schema.user import User
from di.di import DI
from features.integrations.integrations import resolve_any_external_handle
from features.sponsorships.sponsorship_service import SponsorshipService
from util import log
from util.config import config
from util.error_codes import INVALID_PLATFORM, NO_AUTHORIZED_CHATS, SPONSORSHIP_OPERATION_FAILED, UNSPONSOR_SELF_FAILED
from util.errors import InternalError, NotFoundError, ValidationError


class SponsorshipsController:

    __di: DI

    def __init__(self, di: DI):
        self.__di = di

    def fetch_sponsorships(self, user_id_hex: str) -> dict[str, Any]:
        log.d(f"Fetching sponsorships for user '{user_id_hex}'")
        user = self.__di.authorization_service.authorize_for_user(self.__di.invoker, user_id_hex)
        sponsorships_db = self.__di.sponsorship_crud.get_all_by_sponsor(user.id)
        max_sponsorships = (
            config.max_sponsorships_per_user
            if self.__di.invoker.group != UserDB.Group.developer
            else config.max_users
        )
        if not sponsorships_db:
            log.d("  No sponsorships found")
            return {
                "sponsorships": [],
                "max_sponsorships": max_sponsorships,
            }

        sponsorships = [Sponsorship.model_validate(sponsorship_db) for sponsorship_db in sponsorships_db]
        output_sponsorships: list[dict[str, Any]] = []
        for sponsorship in sponsorships:
            receiver_user_db = self.__di.user_crud.get(sponsorship.receiver_id)
            if not receiver_user_db:
                log.t(f"  Receiver user with id {sponsorship.receiver_id} not found, skipping.")
                continue
            receiver_user = User.model_validate(receiver_user_db)
            platform_handle, platform_type = resolve_any_external_handle(receiver_user)
            output_sponsorships.append(
                {
                    "user_id_hex": receiver_user.id.hex,
                    "full_name": receiver_user.full_name,
                    "platform_handle": platform_handle,
                    "platform": platform_type.value if platform_type else None,
                    "sponsored_at": sponsorship.sponsored_at.isoformat(),
                    "accepted_at": sponsorship.accepted_at.isoformat() if sponsorship.accepted_at else None,
                },
            )
        return {
            "sponsorships": output_sponsorships,
            "max_sponsorships": max_sponsorships,
        }

    def sponsor_user(self, sponsor_user_id_hex: str, payload: SponsorshipPayload):
        user = self.__di.authorization_service.authorize_for_user(self.__di.invoker, sponsor_user_id_hex)
        log.d(f"Sponsoring user {payload.platform}/'@{payload.platform_handle}' by '{self.__di.invoker.id.hex}'")
        chat_type = ChatConfigDB.ChatType.lookup(payload.platform)
        if not chat_type:
            raise ValidationError(f"Unsupported platform: {payload.platform}", INVALID_PLATFORM)
        result, message = self.__di.sponsorship_service.sponsor_user(
            sponsor_user_id_hex = user.id.hex,
            receiver_handle = payload.platform_handle,
            chat_type = chat_type,
        )
        if result == SponsorshipService.Result.failure:
            raise InternalError(message, SPONSORSHIP_OPERATION_FAILED)
        log.i(f"  Successfully sponsored '@{payload.platform_handle}'")

    def unsponsor_user(self, sponsor_user_id_hex: str, platform: str, platform_handle: str):
        user = self.__di.authorization_service.authorize_for_user(self.__di.invoker, sponsor_user_id_hex)
        log.d(f"Unsponsoring user {platform}/'@{platform_handle}' by '{self.__di.invoker.id.hex}'")
        chat_type = ChatConfigDB.ChatType.lookup(platform)
        if not chat_type:
            raise ValidationError(f"Unsupported platform: {platform}", INVALID_PLATFORM)
        result, message = self.__di.sponsorship_service.unsponsor_user(
            sponsor_user_id_hex = user.id.hex,
            receiver_handle = platform_handle,
            chat_type = chat_type,
        )
        if result == SponsorshipService.Result.failure:
            raise InternalError(message, SPONSORSHIP_OPERATION_FAILED)
        log.i(f"  Successfully unsponsored '@{platform_handle}'")

    def unsponsor_self(self, user_id_hex: str):
        user = self.__di.authorization_service.authorize_for_user(self.__di.invoker, user_id_hex)
        log.d(f"User '{user.id.hex}' is unsponsoring themselves")
        all_chats = self.__di.authorization_service.get_authorized_chats(user)
        if not all_chats:
            raise NotFoundError("No authorized chats found", NO_AUTHORIZED_CHATS)
        failure_messages: list[str] = []
        successes = 0
        for chat in all_chats:
            result, message = self.__di.sponsorship_service.unsponsor_self(user.id.hex, chat.chat_type)
            if result == SponsorshipService.Result.failure:
                failure_messages.append(message)
                continue
            successes += 1
        if failure_messages:
            log.w(f"Failed to unsponsor self in {len(failure_messages)} chats:\n{'\n  '.join(failure_messages)}")
            if not successes:
                raise InternalError("Failed to unsponsor self in all chats", UNSPONSOR_SELF_FAILED)
        log.i(f"  Successfully unsponsored self in {successes} chats, failed in {len(failure_messages)} chats")
