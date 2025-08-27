import uuid

from db.model.user import UserDB
from db.schema.user import UserSave
from util.config import config

# === Telegram Chat ===

TELEGRAM_AGENT = UserSave(
    full_name = config.telegram_bot_name,
    telegram_username = config.telegram_bot_username,
    telegram_chat_id = str(config.telegram_bot_id),
    telegram_user_id = config.telegram_bot_id,
    group = UserDB.Group.standard,
    id = uuid.uuid5(uuid.NAMESPACE_DNS, config.telegram_bot_username),
)

TELEGRAM_REACTIONS: list[str] = [
    "👍", "👎", "❤", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱", "🤬", "😢", "🎉", "🤩", "🤮", "💩",
    "🙏", "👌", "🕊", "🤡", "🥱", "🥴", "😍", "🐳", "🌚", "🌭", "💯", "🤣", "⚡", "🍌", "🏆",
    "💔", "🤨", "😐", "🍓", "🍾", "💋", "🖕", "😈", "😴", "😭", "🤓", "👻", "👨‍💻", "👀", "🎃", "🙈",
    "😇", "😨", "🤝", "✍", "🤗", "🫡", "🎅", "🎄", "☃", "💅", "🤪", "🗿", "🆒", "💘", "🙉", "🦄",
    "😘", "💊", "🙊", "😎", "👾", "🤷‍♂️", "😡",
]
