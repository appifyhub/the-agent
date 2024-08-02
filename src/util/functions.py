from db.schema.user import User, UserSave
from util.config import config


def is_the_agent(who: User | UserSave | None) -> bool:
    if not who: return False
    return who.telegram_username == config.telegram_bot_username
