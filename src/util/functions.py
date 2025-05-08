import hashlib
import random
from datetime import datetime
from typing import Callable, Any, TypeVar

from db.schema.user import User, UserSave
from features.prompting.prompt_library import TELEGRAM_BOT_USER

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


def mask_secret(secret: str | None = None, mask: str = "*") -> str | None:
    if secret is None:
        return None
    # short strings: mask all
    if len(secret) <= 4:
        return mask * len(secret)
    # medium strings: show one char on each side
    if len(secret) <= 8:
        return secret[0] + (mask * (len(secret) - 2)) + secret[-1:]
    # long strings: show 3 chars on each end with 5 masks in the middle
    return secret[:3] + (mask * 5) + secret[-3:]


###           U N T E S T E D           ###
# No idea how to test other than manually #

def digest_md5(content: str) -> str:
    # noinspection InsecureHash
    hash_object = hashlib.md5()
    hash_object.update(content.encode("utf-8"))
    return hash_object.hexdigest()
