import hashlib
import random
from datetime import datetime, timedelta
from typing import Callable, Any, TypeVar

from db.schema.user import User, UserSave
from features.prompting.prompt_library import TELEGRAM_BOT_USER
from util.safe_printer_mixin import sprint

K = TypeVar("K")
V = TypeVar("V")


def is_the_agent(who: User | UserSave | None) -> bool:
    if not who:
        return False
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


def first_key_with_value(source: dict[K, V], value: V) -> K | None:
    for k, v in source.items():
        if v == value:
            return k
    return None


###           U N T E S T E D           ###
# No idea how to test other than manually #

def nearest_hour_epoch() -> int:
    now = datetime.now()
    last_hour_mark: datetime = now.replace(minute = 0, second = 0, microsecond = 0)
    next_hour_mark: datetime = last_hour_mark + timedelta(hours = 1)
    sprint(f"Nearest hour at {now} is {next_hour_mark}")
    return int(next_hour_mark.timestamp())


def digest_md5(content: str) -> str:
    # noinspection InsecureHash
    hash_object = hashlib.md5()
    hash_object.update(content.encode("utf-8"))
    return hash_object.hexdigest()
