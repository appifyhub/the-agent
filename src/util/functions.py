import hashlib
from typing import Any, Callable, TypeVar
from uuid import uuid4

from pydantic import SecretStr

K = TypeVar("K")
V = TypeVar("V")


def generate_short_uuid() -> str:
    return uuid4().hex[:8]


def generate_deterministic_short_uuid(seed: str) -> str:
    # noinspection InsecureHash
    hash_digest = hashlib.sha256(seed.encode()).hexdigest()
    return hash_digest[:8]


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


def mask_secret(secret: str | SecretStr | None = None, mask: str = "*") -> str | None:
    if secret is None:
        return None
    # extract the secret value
    if isinstance(secret, SecretStr):
        secret = secret.get_secret_value()
    # short strings: mask all
    if len(secret) <= 4:
        return mask * len(secret)
    # medium strings: show one char on each side
    if len(secret) <= 8:
        return secret[0] + (mask * (len(secret) - 2)) + secret[-1:]
    # long strings: show 3 chars on each end with 5 masks in the middle
    return secret[:3] + (mask * 5) + secret[-3:]


def digest_md5(content: str) -> str:
    # noinspection InsecureHash
    hash_object = hashlib.md5()
    hash_object.update(content.encode("utf-8"))
    return hash_object.hexdigest()


def normalize_phone_number(phone: str | None) -> str | None:
    if phone is None:
        return None
    return "".join(c for c in phone if c.isdigit())


def normalize_username(username: str | None) -> str | None:
    if username is None:
        return None
    return username.replace("@", "").replace("+", "").replace(" ", "").strip()


def extract_url_from_replicate_result(result: Any) -> str:
    if isinstance(result, list):
        if not result:
            raise ValueError("Empty result list from Replicate")
        first_item = result[0]
        if hasattr(first_item, "url"):
            return first_item.url
        elif isinstance(first_item, str):
            return first_item
        raise ValueError(f"Unexpected result type in list: {type(first_item)}")
    elif hasattr(result, "url"):
        return result.url  # type: ignore
    elif isinstance(result, str):
        return result
    raise ValueError(f"Unexpected result type from Replicate: {type(result)}")
