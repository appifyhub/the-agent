import random
from datetime import datetime
from typing import Callable, Any

from db.schema.user import User, UserSave
from features.prompting.predefined_prompts import TELEGRAM_BOT_USER


def is_the_agent(who: User | UserSave | None) -> bool:
    if not who: return False
    return who.telegram_username == TELEGRAM_BOT_USER.telegram_username


def construct_bot_message_id(chat_id: str, sent_at: datetime) -> str:
    random_seed = str(random.randint(1000, 9999))
    formatted_time = sent_at.strftime("%y%m%d%H%M%S")
    result = f"{chat_id}-{formatted_time}-{random_seed}"
    return result


def silent(func: Callable[..., Any]) -> Callable[..., Any]:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception:
            return None

    return wrapper
