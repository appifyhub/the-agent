import uuid

from pydantic import SecretStr

from db.model.user import UserDB
from db.schema.user import UserSave
from util.config import config

# === Background Tasks ===

BACKGROUND_AGENT = UserSave(
    id = uuid.uuid5(uuid.NAMESPACE_DNS, "the-agent-background"),
    full_name = config.background_bot_name,
    group = UserDB.Group.standard,
)


# === GitHub Tasks ===

GITHUB_AGENT = UserSave(
    id = uuid.uuid5(uuid.NAMESPACE_DNS, config.github_bot_username),
    full_name = config.github_bot_name,
    group = UserDB.Group.standard,
)


# === Telegram Tasks ===

TELEGRAM_AGENT = UserSave(
    id = uuid.uuid5(uuid.NAMESPACE_DNS, config.telegram_bot_username),
    full_name = config.telegram_bot_name,
    group = UserDB.Group.standard,
    telegram_username = config.telegram_bot_username,
    telegram_chat_id = str(config.telegram_bot_id),
    telegram_user_id = config.telegram_bot_id,
)

TELEGRAM_REACTIONS: list[str] = [
    "👍", "👎", "❤", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱", "🤬", "😢", "🎉", "🤩", "🤮", "💩",
    "🙏", "👌", "🕊", "🤡", "🥱", "🥴", "😍", "🐳", "🌚", "🌭", "💯", "🤣", "⚡", "🍌", "🏆",
    "💔", "🤨", "😐", "🍓", "🍾", "💋", "🖕", "😈", "😴", "😭", "🤓", "👻", "👨‍💻", "👀", "🎃", "🙈",
    "😇", "😨", "🤝", "✍", "🤗", "🫡", "🎅", "🎄", "☃", "💅", "🤪", "🗿", "🆒", "💘", "🙉", "🦄",
    "😘", "💊", "🙊", "😎", "👾", "🤷‍♂️", "😡",
]


# === WhatsApp Tasks ===

WHATSAPP_AGENT = UserSave(
    id = uuid.uuid5(uuid.NAMESPACE_DNS, config.whatsapp_bot_phone_number),
    full_name = config.whatsapp_bot_name,
    group = UserDB.Group.standard,
    whatsapp_user_id = config.whatsapp_phone_number_id,
    whatsapp_phone_number = SecretStr(config.whatsapp_bot_phone_number),
)

WHATSAPP_REACTIONS: list[str] = [
    "👍", "👎", "❤", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱", "🤬", "😢", "🎉", "🤩", "🤮", "💩",
    "🙏", "👌", "🕊", "🤡", "🥱", "🥴", "😍", "🐳", "🌚", "🌭", "💯", "🤣", "⚡", "🍌", "🏆",
    "💔", "🤨", "😐", "🍓", "🍾", "💋", "🖕", "😈", "😴", "😭", "🤓", "👻", "👨‍💻", "👀", "🎃", "🙈",
    "😇", "😨", "🤝", "✍", "🤗", "🫡", "🎅", "🎄", "☃", "💅", "🤪", "🗿", "🆒", "💘", "🙉", "🦄",
    "😘", "💊", "🙊", "😎", "👾", "🤷‍♂️", "😡",
]
