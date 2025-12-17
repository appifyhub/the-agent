import uuid

from pydantic import SecretStr

from db.model.user import UserDB
from db.schema.user import UserSave
from util.config import config

# === The Agent User ===

THE_AGENT = UserSave(
    id = uuid.uuid5(uuid.NAMESPACE_DNS, "the-agent"),
    full_name = config.agent_bot_name,
    group = UserDB.Group.standard,
    telegram_username = config.telegram_bot_username,
    telegram_chat_id = str(config.telegram_bot_id),
    telegram_user_id = config.telegram_bot_id,
    whatsapp_user_id = config.whatsapp_phone_number_id,
    whatsapp_phone_number = SecretStr(config.whatsapp_bot_phone_number),
)

# === Background Tasks Agent (runs scheduled/background tasks) ===

BACKGROUND_AGENT = UserSave(
    id = uuid.uuid5(uuid.NAMESPACE_DNS, "the-agent-background"),
    full_name = config.background_bot_name,
    group = UserDB.Group.standard,
)

# === Platform Reactions ===

TELEGRAM_REACTIONS: list[str] = [
    "👍", "👎", "❤", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱", "🤬", "😢", "🎉", "🤩", "🤮", "💩",
    "🙏", "👌", "🕊", "🤡", "🥱", "🥴", "😍", "🐳", "🌚", "🌭", "💯", "🤣", "⚡", "🍌", "🏆", "💔",
    "🤨", "😐", "🍓", "🍾", "💋", "🖕", "😈", "😴", "😭", "🤓", "👻", "👨‍💻", "👀", "🎃", "🙈", "😇",
    "😨", "🤝", "✍", "🤗", "🫡", "🎅", "🎄", "☃", "💅", "🤪", "🗿", "🆒", "💘", "🙉", "🦄", "😘",
    "💊", "🙊", "😎", "👾", "🤷‍♂️", "😡",
]

WHATSAPP_REACTIONS: list[str] = [
    "👍", "👎", "❤", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱", "🤬", "😢", "🎉", "🤩", "🤮", "💩",
    "🙏", "👌", "🕊", "🤡", "🥱", "🥴", "😍", "🐳", "🌚", "🌭", "💯", "🤣", "⚡", "🍌", "🏆",
    "💔", "🤨", "😐", "🍓", "🍾", "💋", "🖕", "😈", "😴", "😭", "🤓", "👻", "👨‍💻", "👀", "🎃", "🙈",
    "😇", "😨", "🤝", "✍", "🤗", "🫡", "🎅", "🎄", "☃", "💅", "🤪", "🗿", "🆒", "💘", "🙉", "🦄",
    "😘", "💊", "🙊", "😎", "👾", "🤷‍♂️", "😡",
]

# === Platform Notification Intervals (in seconds) ===

TELEGRAM_REACTION_INTERVAL_S = 10
TELEGRAM_REACTION_INITIAL_DELAY_S = TELEGRAM_REACTION_INTERVAL_S

WHATSAPP_REACTION_INTERVAL_S = 7
WHATSAPP_REACTION_INITIAL_DELAY_S = 0

# === Platform Photo Size Limits (in bytes, when sending via HTTP URL) ===

TELEGRAM_MAX_PHOTO_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB (10 MB for multipart upload, but we use URLs)
WHATSAPP_MAX_PHOTO_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
