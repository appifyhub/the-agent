from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from db.model.user import UserDB


class UserBase(BaseModel):
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
    tool_choice_llm: str | None = None
    tool_choice_vision: str | None = None
    tool_choice_hearing: str | None = None
    tool_choice_images: str | None = None
    tool_choice_search: str | None = None
    tool_choice_embedding: str | None = None
    tool_choice_api: str | None = None
    group: UserDB.Group = UserDB.Group.standard


class UserSave(UserBase):
    id: UUID | None = None


class User(UserBase):
    id: UUID
    created_at: date
    model_config = ConfigDict(from_attributes = True)

    def has_any_api_key(self) -> bool:
        return any(
            [
                self.open_ai_key,
                self.anthropic_key,
                self.perplexity_key,
                self.replicate_key,
                self.rapid_api_key,
                self.coinmarketcap_key,
            ],
        )

    def has_any_tool_choice(self) -> bool:
        return any(
            [
                self.tool_choice_llm,
                self.tool_choice_vision,
                self.tool_choice_hearing,
                self.tool_choice_images,
                self.tool_choice_search,
                self.tool_choice_embedding,
                self.tool_choice_api,
            ],
        )
