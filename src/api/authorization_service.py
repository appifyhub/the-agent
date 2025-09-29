from uuid import UUID

from db.schema.chat_config import ChatConfig
from db.schema.user import User
from di.di import DI
from features.integrations.integrations import is_own_chat, lookup_all_admin_chats
from util import log
from util.config import config


class AuthorizationService:

    __di: DI

    def __init__(self, di: DI):
        self.__di = di

    def validate_chat(self, chat: str | UUID | ChatConfig) -> ChatConfig:
        if isinstance(chat, ChatConfig):
            return chat

        log.d(f"Validating chat data for '{chat}'")
        chat_uuid = chat if isinstance(chat, UUID) else UUID(hex = chat)
        chat_config_db = self.__di.chat_config_crud.get(chat_uuid)
        if not chat_config_db:
            raise ValueError(log.e(f"Chat '{chat}' not found"))
        return ChatConfig.model_validate(chat_config_db)

    def validate_user(self, user: str | UUID | User) -> User:
        if isinstance(user, User):
            return user

        user_db = self.__di.user_crud.get(user if isinstance(user, UUID) else UUID(hex = user))
        if not user_db:
            raise ValueError(log.e(f"User '{user}' not found"))
        return User.model_validate(user_db)

    def get_authorized_chats(self, user: str | UUID | User) -> list[ChatConfig]:
        user = self.validate_user(user)
        log.d(f"Getting administered chats for user {user.id.hex}")

        log.t("  Validating chat configurations")
        max_chats = config.max_users * 10  # assuming each user administers 10 chats
        all_chat_configs_db = self.__di.chat_config_crud.get_all(limit = max_chats)
        if not all_chat_configs_db:
            log.t("  No chat configurations found in DB")
            return []
        all_chat_configs = [ChatConfig.model_validate(chat_config_db) for chat_config_db in all_chat_configs_db]
        log.t(f"  Found {len(all_chat_configs)} chat configurations to check")

        log.t("  Checking admin status in each chat")
        administered_chats: list[ChatConfig] = []
        for chat_config in all_chat_configs:
            log.t(f"    Checking {chat_config.chat_type.value} chat: {chat_config.title} ({chat_config.chat_id})")
            try:
                # first we check if this is user's private chat with the agent
                is_private_admin = is_own_chat(chat_config, user)
                if is_private_admin:
                    log.t(f"    Chat {chat_config.chat_id} is private and matches invoker's external chat ID")
                    administered_chats.append(chat_config)
                    continue
                else:
                    log.t(f"    Chat {chat_config.chat_id} does not match invoker's external chat ID")

                # it's not the user's private admin chat at this point.
                # now, if it's a private chat, we can continue without checking platform admin status
                if chat_config.is_private:
                    continue

                # it's not a private chat at this point. we can check if the user is admin on the platform
                platform_admin_chats = lookup_all_admin_chats(chat_config, user, self.__di)
                if platform_admin_chats:
                    log.t(f"    User {user.id.hex} is platform admin for chat {chat_config.chat_id}")
                    administered_chats.extend(platform_admin_chats)
                    continue
                else:
                    log.t(f"    User {user.id.hex} is not platform admin for chat {chat_config.chat_id}")
            except Exception as e:
                log.t(f"    Error checking administrators for '{chat_config.chat_id}'", e)

        log.t("  Sorting administered chats now")
        administered_chats.sort(
            key = lambda chat: (
                not chat.is_private,
                chat.chat_type.value,
                chat.title.lower() if chat.title else "",
                chat.external_id or "",
                chat.chat_id.hex,
            ),
        )
        log.i(f"  Found {len(administered_chats)} administered chats")
        return administered_chats

    def authorize_for_chat(self, invoker_user: str | UUID | User, target_chat: str | UUID | ChatConfig) -> ChatConfig:
        invoker_user = self.validate_user(invoker_user)
        chat_display = target_chat if isinstance(target_chat, (str, UUID)) else target_chat.chat_id
        log.d(f"Validating admin rights for invoker in chat '{chat_display}'")
        chat_config = self.validate_chat(target_chat)
        admin_chat_configs = self.get_authorized_chats(invoker_user)
        for admin_chat_config in admin_chat_configs:
            if admin_chat_config.chat_id == chat_config.chat_id:
                return chat_config
        raise ValueError(log.e(f"User '{invoker_user.id.hex}' is not admin in '{chat_config.title}'"))

    def authorize_for_user(self, invoker_user: str | UUID | User, target_user: str | UUID | User) -> User:
        invoker_user = self.validate_user(invoker_user)
        target_user = self.validate_user(target_user)
        log.d(f"Authorizing user '{invoker_user.id.hex}' to access user '{target_user.id.hex}'")
        if invoker_user.id != target_user.id:
            raise ValueError(log.e(f"Target user '{target_user.id.hex}' is not the allowed user '{invoker_user.id.hex}'"))
        return target_user
