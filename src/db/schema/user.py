from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, SecretStr

from db.model.user import UserDB


class UserBase(BaseModel):
    full_name: str | None = None

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
    tool_choice_images_restoration: str | None = None
    tool_choice_images_inpainting: str | None = None
    tool_choice_images_background_removal: str | None = None
    tool_choice_search: str | None = None
    tool_choice_embedding: str | None = None
    tool_choice_api_fiat_exchange: str | None = None
    tool_choice_api_crypto_exchange: str | None = None
    tool_choice_api_twitter: str | None = None

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
    model_config = ConfigDict(from_attributes = True)

    def has_any_api_key(self) -> bool:
        secret_fields = self._get_secret_str_fields()
        return any(getattr(self, field) is not None for field in secret_fields)
