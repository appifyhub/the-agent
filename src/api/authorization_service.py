from uuid import UUID

from db.crud.chat_config import ChatConfigCRUD
from db.crud.user import UserCRUD
from db.schema.chat_config import ChatConfig
from db.schema.user import User
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


class AuthorizationService(SafePrinterMixin):
    __telegram_sdk: TelegramBotSDK
    __user_dao: UserCRUD
    __chat_config_dao: ChatConfigCRUD

    def __init__(
        self,
        telegram_sdk: TelegramBotSDK,
        user_dao: UserCRUD,
        chat_config_dao: ChatConfigCRUD,
    ):
        super().__init__(config.verbose)
        self.__telegram_sdk = telegram_sdk
        self.__user_dao = user_dao
        self.__chat_config_dao = chat_config_dao

    def validate_chat(self, chat: str | ChatConfig) -> ChatConfig:
        if isinstance(chat, ChatConfig):
            return chat

        self.sprint("Validating chat data")
        chat_config_db = self.__chat_config_dao.get(chat)
        if not chat_config_db:
            message = f"Chat '{chat}' not found"
            self.sprint(message)
            raise ValueError(message)
        return ChatConfig.model_validate(chat_config_db)

    def validate_user(self, user: str | UUID | User) -> User:
        if isinstance(user, User):
            return user

        user_db = self.__user_dao.get(user if isinstance(user, UUID) else UUID(hex = user))
        if not user_db:
            message = f"User '{user}' not found"
            self.sprint(message)
            raise ValueError(message)
        return User.model_validate(user_db)

    def get_authorized_chats(self, user: str | UUID | User) -> list[ChatConfig]:
        user = self.validate_user(user)
        self.sprint(f"Getting administered chats for user {user.id.hex}")

        if not user.telegram_user_id:
            self.sprint(f"  User {user.id.hex} has no telegram_user_id")
            return []

        self.sprint("  Validating chat configurations")
        max_chats = config.max_users * 10  # assuming each user administers 10 chats
        all_chat_configs_db = self.__chat_config_dao.get_all(limit = max_chats)
        if not all_chat_configs_db:
            self.sprint("  No chat configurations found in DB")
            return []
        all_chat_configs = [ChatConfig.model_validate(chat_config_db) for chat_config_db in all_chat_configs_db]
        self.sprint(f"  Found {len(all_chat_configs)} chat configurations to check")

        self.sprint("  Checking admin status in each chat")
        administered_chats: list[ChatConfig] = []
        for chat_config in all_chat_configs:
            self.sprint(f"    Checking chat: {chat_config.title} ({chat_config.chat_id})")
            try:
                if chat_config.is_private:
                    if user.telegram_chat_id == chat_config.chat_id:
                        self.sprint(f"    Chat {chat_config.chat_id} is private and matches invoker's chat ID")
                        administered_chats.append(chat_config)
                    else:
                        self.sprint(f"    Chat {chat_config.chat_id} is private but does not match invoker's chat ID")
                    continue

                administrators = self.__telegram_sdk.get_chat_administrators(chat_config.chat_id)
                if not administrators:
                    self.sprint(f"    No administrators returned for chat {chat_config.chat_id}")
                    continue
                for admin_member in administrators:
                    if admin_member.user and admin_member.user.id == user.telegram_user_id:
                        self.sprint(f"    User {admin_member.user.id} IS admin in '{chat_config.chat_id}'")
                        administered_chats.append(chat_config)
                        break
                else:
                    self.sprint(f"    User {user.telegram_user_id} is NOT admin in '{chat_config.chat_id}'")
            except Exception as e:
                self.sprint(f"    Error checking administrators for '{chat_config.chat_id}'", e)

        self.sprint("  Sorting administered chats now")
        administered_chats.sort(
            key = lambda chat: (
                not chat.is_private,
                chat.title.lower() if chat.title else "",
                chat.chat_id,
            ),
        )
        return administered_chats

    def authorize_for_chat(self, invoker_user: str | UUID | User, target_chat: str | ChatConfig) -> ChatConfig:
        invoker_user = self.validate_user(invoker_user)
        chat_display = target_chat if isinstance(target_chat, str) else target_chat.chat_id
        self.sprint(f"Validating admin rights for invoker in chat '{chat_display}'")
        chat_config = self.validate_chat(target_chat)
        admin_chat_configs = self.get_authorized_chats(invoker_user)
        for admin_chat_config in admin_chat_configs:
            if admin_chat_config.chat_id == chat_config.chat_id:
                return chat_config
        message = f"User '{invoker_user.id.hex}' is not admin in '{chat_config.title}'"
        self.sprint(message)
        raise ValueError(message)

    def authorize_for_user(self, invoker_user: str | UUID | User, target_user: str | UUID | User) -> User:
        invoker_user = self.validate_user(invoker_user)
        target_user = self.validate_user(target_user)
        if invoker_user.id != target_user.id:
            user_display = target_user if isinstance(target_user, str) else str(target_user)
            message = f"Target user '{user_display}' is not the allowed user '{invoker_user.id.hex}'"
            self.sprint(message)
            raise ValueError(message)
        return target_user
