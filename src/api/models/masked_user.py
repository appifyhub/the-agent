from pydantic import BaseModel

from db.schema.user import User
from util.functions import mask_secret


class MaskedUser(BaseModel):
    id: str
    full_name: str | None = None
    telegram_username: str | None = None
    telegram_chat_id: str | None = None
    telegram_user_id: int | None = None
    open_ai_key: str | None = None
    anthropic_key: str | None = None
    perplexity_key: str | None = None
    replicate_key: str | None = None
    rapid_api_key: str | None = None
    coinmarketcap_key: str | None = None
    group: str
    created_at: str

    @staticmethod
    def from_user(user: User) -> "MaskedUser":
        return MaskedUser(
            id = user.id.hex,
            full_name = user.full_name,
            telegram_username = user.telegram_username,
            telegram_chat_id = user.telegram_chat_id,
            telegram_user_id = user.telegram_user_id,
            open_ai_key = mask_secret(user.open_ai_key),
            anthropic_key = mask_secret(user.anthropic_key),
            perplexity_key = mask_secret(user.perplexity_key),
            replicate_key = mask_secret(user.replicate_key),
            rapid_api_key = mask_secret(user.rapid_api_key),
            coinmarketcap_key = mask_secret(user.coinmarketcap_key),
            group = user.group.value,
            created_at = user.created_at.isoformat(),
        )
