import secrets
from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from db.model.user import UserDB


def generate_connect_key() -> str:
    # the final format is XXXX-XXXX-XXXX
    allowed_chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # avoids confusing characters like I, O, 1, 0, etc.
    key_chars = [secrets.choice(allowed_chars) for _ in range(12)]
    return f"{''.join(key_chars[0:4])}-{''.join(key_chars[4:8])}-{''.join(key_chars[8:12])}"


class UserBase(BaseModel):
    full_name: str | None = None
    about_me: SecretStr | None = None

    telegram_username: str | None = None
    telegram_chat_id: str | None = None
    telegram_user_id: int | None = None

    whatsapp_user_id: str | None = None
    whatsapp_phone_number: SecretStr | None = None

    open_ai_key: SecretStr | None = None
    anthropic_key: SecretStr | None = None
    google_ai_key: SecretStr | None = None
    perplexity_key: SecretStr | None = None
    replicate_key: SecretStr | None = None
    rapid_api_key: SecretStr | None = None
    coinmarketcap_key: SecretStr | None = None

    tool_choice_chat: str | None = None
    tool_choice_reasoning: str | None = None
    tool_choice_copywriting: str | None = None
    tool_choice_vision: str | None = None
    tool_choice_hearing: str | None = None
    tool_choice_images_gen: str | None = None
    tool_choice_images_edit: str | None = None
    tool_choice_search: str | None = None
    tool_choice_embedding: str | None = None
    tool_choice_api_fiat_exchange: str | None = None
    tool_choice_api_crypto_exchange: str | None = None
    tool_choice_api_twitter: str | None = None

    credit_balance: float = 0.0

    group: UserDB.Group = UserDB.Group.standard

    @classmethod
    def _get_secret_str_fields(cls) -> list[str]:
        """Get all field names that are SecretStr type."""
        secret_fields = []
        for field_name, field_info in cls.model_fields.items():
            # Check if the field annotation contains SecretStr
            field_type = field_info.annotation
            # Handle both SecretStr and SecretStr | None
            if field_type is SecretStr:
                secret_fields.append(field_name)
            elif hasattr(field_type, "__args__") and SecretStr in getattr(field_type, "__args__", ()):
                secret_fields.append(field_name)
        return secret_fields


class UserSave(UserBase):
    id: UUID | None = None
    connect_key: str | None = None

    @model_validator(mode = "after")
    def _ensure_connect_key(self) -> "UserSave":
        if not self.connect_key:
            self.connect_key = generate_connect_key()
        return self

    def model_dump(self, **kwargs) -> dict:
        # we override to automatically convert SecretStr fields for database storage
        data = super().model_dump(**kwargs)
        secret_fields = self._get_secret_str_fields()
        for field in secret_fields:
            if data.get(field) is not None:
                data[field] = data[field].get_secret_value() if hasattr(data[field], "get_secret_value") else data[field]
        return data


class User(UserBase):
    id: UUID
    created_at: date
    connect_key: str = Field(default_factory = generate_connect_key)
    model_config = ConfigDict(from_attributes = True)

    def has_any_api_key(self) -> bool:
        api_key_fields = [
            "open_ai_key",
            "anthropic_key",
            "google_ai_key",
            "perplexity_key",
            "replicate_key",
            "rapid_api_key",
            "coinmarketcap_key",
        ]
        return any(getattr(self, field) is not None for field in api_key_fields)
