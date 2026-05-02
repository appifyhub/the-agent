from uuid import UUID

from db.schema.chat_config import ChatConfig
from db.schema.user import User
from di.di import DI
from features.chat.membership.chat_membership import ChatMembership
from util import log


class ChatMembershipService:

    __di: DI

    def __init__(self, di: DI):
        self.__di = di

    def get_or_create(self, user: User, chat: ChatConfig) -> ChatMembership:
        existing = self.__di.chat_membership_repo.get(user.id, chat.chat_id)
        if existing is not None:
            return existing
        log.t(f"  No membership row found for user '{user.id.hex}' in chat '{chat.chat_id.hex}', creating one")
        is_admin = self.__di.platform_bot_sdk().resolve_member_is_admin(chat, user)
        return self.__di.chat_membership_repo.save(
            ChatMembership(
                user_id = user.id,
                chat_id = chat.chat_id,
                is_admin = is_admin,
                use_about_me = True,
                use_custom_prompt = True,
            ),
        )

    def get(self, user_id: UUID, chat_id: UUID) -> ChatMembership | None:
        return self.__di.chat_membership_repo.get(user_id, chat_id)

    def get_all_for_user(self, user_id: UUID) -> list[ChatMembership]:
        return self.__di.chat_membership_repo.get_all_for_user(user_id)

    def save(self, membership: ChatMembership) -> ChatMembership:
        return self.__di.chat_membership_repo.save(membership)

    def refresh_chat_memberships(self, user: User, current_admin_chats: list[ChatConfig]) -> list[ChatMembership]:
        admin_chat_ids: set[UUID] = {chat.chat_id for chat in current_admin_chats}
        existing_memberships = self.__di.chat_membership_repo.get_all_for_user(user.id)
        existing_by_chat_id = {m.chat_id: m for m in existing_memberships}

        for chat_id in admin_chat_ids:
            existing = existing_by_chat_id.get(chat_id)
            if existing is None:
                self.__di.chat_membership_repo.save(
                    ChatMembership(
                        user_id = user.id,
                        chat_id = chat_id,
                        is_admin = True,
                        use_about_me = True,
                        use_custom_prompt = True,
                    ),
                )
            elif not existing.is_admin:
                self.__di.chat_membership_repo.save(
                    ChatMembership(
                        user_id = user.id,
                        chat_id = chat_id,
                        is_admin = True,
                        use_about_me = existing.use_about_me,
                        use_custom_prompt = existing.use_custom_prompt,
                    ),
                )

        for chat_id, existing in existing_by_chat_id.items():
            if existing.is_admin and chat_id not in admin_chat_ids:
                self.__di.chat_membership_repo.save(
                    ChatMembership(
                        user_id = user.id,
                        chat_id = chat_id,
                        is_admin = False,
                        use_about_me = existing.use_about_me,
                        use_custom_prompt = existing.use_custom_prompt,
                    ),
                )

        return self.__di.chat_membership_repo.get_all_for_user(user.id)
