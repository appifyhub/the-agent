from pydantic import SecretStr

from db.crud.user import UserCRUD
from db.model.chat_config import ChatConfigDB
from db.model.user import UserDB
from db.schema.chat_config import ChatConfig
from db.schema.user import User, UserSave
from di.di import DI
from features.integrations.integration_config import BACKGROUND_AGENT, THE_AGENT
from util.functions import normalize_phone_number, normalize_username


def resolve_agent_user(chat_type: ChatConfigDB.ChatType) -> UserSave:
    match chat_type:
        case ChatConfigDB.ChatType.telegram | ChatConfigDB.ChatType.whatsapp | ChatConfigDB.ChatType.github:
            return THE_AGENT
        case ChatConfigDB.ChatType.background:
            return BACKGROUND_AGENT


def resolve_external_id(user: User | UserSave, chat_type: ChatConfigDB.ChatType) -> str | None:
    match chat_type:
        case ChatConfigDB.ChatType.telegram:
            return str(user.telegram_user_id) if user.telegram_user_id else None
        case ChatConfigDB.ChatType.whatsapp:
            return user.whatsapp_user_id
        case ChatConfigDB.ChatType.background:
            return None
        case ChatConfigDB.ChatType.github:
            return None


def resolve_external_handle(user: User | UserSave, chat_type: ChatConfigDB.ChatType) -> str | None:
    match chat_type:
        case ChatConfigDB.ChatType.telegram:
            return user.telegram_username
        case ChatConfigDB.ChatType.whatsapp:
            return user.whatsapp_phone_number.get_secret_value() if user.whatsapp_phone_number else None
        case ChatConfigDB.ChatType.background:
            return None
        case ChatConfigDB.ChatType.github:
            return None


def resolve_any_external_handle(user: User | UserSave) -> tuple[str | None, ChatConfigDB.ChatType | None]:
    for chat_type in ChatConfigDB.ChatType:
        handle = resolve_external_handle(user, chat_type)
        if handle and handle.strip():
            return handle.strip(), chat_type
    return None, None


def resolve_user_link(user: User | UserSave, chat_type: ChatConfigDB.ChatType) -> str | None:
    platform_handle = resolve_external_handle(user, chat_type)
    if not platform_handle:
        return None

    clean_handle: str
    if chat_type == ChatConfigDB.ChatType.whatsapp:
        clean_handle = str(normalize_phone_number(platform_handle)).strip()
    else:
        clean_handle = platform_handle.lstrip("@").lstrip("+").lstrip("/").strip()
    if not clean_handle:
        return None

    match chat_type:
        case ChatConfigDB.ChatType.telegram:
            return f"[@{clean_handle}](https://t.me/{clean_handle})"
        case ChatConfigDB.ChatType.whatsapp:
            return f"[{clean_handle}](https://wa.me/{clean_handle})"
        case ChatConfigDB.ChatType.background:
            return None
        case ChatConfigDB.ChatType.github:
            return f"[@{clean_handle}](https://github.com/{clean_handle})"


def resolve_platform_name(chat_type: ChatConfigDB.ChatType) -> str | None:
    match chat_type:
        case ChatConfigDB.ChatType.telegram:
            return "Telegram"
        case ChatConfigDB.ChatType.whatsapp:
            return "WhatsApp"
        case ChatConfigDB.ChatType.background:
            return "Pulse"
        case ChatConfigDB.ChatType.github:
            return "GitHub"


def resolve_private_chat_id(user: User | UserSave, chat_type: ChatConfigDB.ChatType) -> str | None:
    match chat_type:
        case ChatConfigDB.ChatType.telegram:
            return user.telegram_chat_id
        case ChatConfigDB.ChatType.whatsapp:
            return user.whatsapp_user_id
        case ChatConfigDB.ChatType.background:
            return None
        case ChatConfigDB.ChatType.github:
            return None


def resolve_user_to_save(handle: str, chat_type: ChatConfigDB.ChatType) -> UserSave | None:
    match chat_type:
        case ChatConfigDB.ChatType.telegram:
            normalized_username = (normalize_username(handle) or "").strip()
            return UserSave(
                id = None,
                full_name = None,
                telegram_username = normalized_username,
                telegram_chat_id = None,
                telegram_user_id = None,
                group = UserDB.Group.standard,
            )
        case ChatConfigDB.ChatType.background:
            return None
        case ChatConfigDB.ChatType.github:
            return None
        case ChatConfigDB.ChatType.whatsapp:
            normalized_phone = (normalize_phone_number(handle) or "").strip()
            return UserSave(
                id = None,
                full_name = None,
                whatsapp_user_id = normalized_phone,
                whatsapp_phone_number = SecretStr(normalized_phone),
                group = UserDB.Group.standard,
            )


def is_the_agent(who: User | UserSave | None, chat_type: ChatConfigDB.ChatType) -> bool:
    if not who:
        return False
    agent_user = resolve_agent_user(chat_type)
    user_id = resolve_external_id(who, chat_type)
    agent_id = resolve_external_id(agent_user, chat_type)
    return user_id is not None and user_id == agent_id


def is_own_chat(chat_config: ChatConfig, user: User) -> bool:
    match chat_config.chat_type:
        case ChatConfigDB.ChatType.telegram:
            is_own_chat_configured = (user.telegram_chat_id is not None) and (chat_config.external_id is not None)
            return chat_config.is_private and is_own_chat_configured and user.telegram_chat_id == chat_config.external_id
        case ChatConfigDB.ChatType.whatsapp:
            is_own_chat_configured = (user.whatsapp_user_id is not None) and (chat_config.external_id is not None)
            normalized_user_id = normalize_phone_number(user.whatsapp_user_id) or ""
            normalized_external_id = normalize_phone_number(chat_config.external_id) or ""
            return chat_config.is_private and is_own_chat_configured and normalized_user_id == normalized_external_id
        case ChatConfigDB.ChatType.background:
            return False
        case ChatConfigDB.ChatType.github:
            return False


def lookup_user_by_handle(handle: str, chat_type: ChatConfigDB.ChatType, user_crud: UserCRUD) -> UserDB | None:
    match chat_type:
        case ChatConfigDB.ChatType.telegram:
            normalized_username = (normalize_username(handle) or "").strip()
            return user_crud.get_by_telegram_username(normalized_username)
        case ChatConfigDB.ChatType.whatsapp:
            normalized_phone = (normalize_phone_number(handle) or "").strip()
            # Try by whatsapp_user_id first (not encrypted, faster), then fall back to phone number
            user = user_crud.get_by_whatsapp_user_id(normalized_phone)
            if not user:
                user = user_crud.get_by_whatsapp_phone_number(normalized_phone)
            return user
        case ChatConfigDB.ChatType.background:
            return None
        case ChatConfigDB.ChatType.github:
            return None


def add_messaging_frequency_warning(response_data: dict, chat_type: ChatConfigDB.ChatType | None) -> None:
    if chat_type == ChatConfigDB.ChatType.whatsapp:
        response_data["warning"] = (
            "WhatsApp's 24-hour messaging window: Notifications will only be delivered if "
            "you've messaged the agent within the last 24 hours. If you haven't sent a message "
            "recently, you won't receive this alert notification."
        )


def lookup_all_admin_chats(chat_config: ChatConfig, user: User, di: DI) -> list[ChatConfig]:
    match chat_config.chat_type:
        case ChatConfigDB.ChatType.telegram:
            administrators = di.telegram_bot_sdk.get_chat_administrators(str(chat_config.external_id))
            if not administrators:
                return []
            result: list[ChatConfig] = []
            for admin_member in administrators:
                if admin_member.user and admin_member.user.id == user.telegram_user_id:
                    result.append(chat_config)
                    break
            return result
        case ChatConfigDB.ChatType.whatsapp:
            return []
        case ChatConfigDB.ChatType.background:
            return []
        case ChatConfigDB.ChatType.github:
            return []
