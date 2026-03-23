from dataclasses import dataclass
from enum import Enum

from features.external_tools.external_tool import ToolType
from features.external_tools.external_tool_library import (
    CLAUDE_4_6_OPUS,
    CLAUDE_4_6_SONNET,
    CRYPTO_CURRENCY_EXCHANGE,
    FIAT_CURRENCY_EXCHANGE,
    GPT_4_1_NANO,
    GPT_4O_MINI_TRANSCRIBE,
    GPT_4O_TRANSCRIBE,
    GPT_5_2,
    GPT_5_4,
    GPT_5_4_PRO,
    GPT_5_NANO,
    IMAGE_GEN_EDIT_FLUX_2_PRO,
    IMAGE_GEN_EDIT_GOOGLE_NANO_BANANA_2,
    IMAGE_GEN_EDIT_SEEDREAM_4,
    SONAR,
    SONAR_PRO,
    SONAR_REASONING_PRO,
    TEXT_EMBEDDING_3_SMALL,
    TEXT_EMBEDDING_5_LARGE,
    WHISPER_1,
    X_READ_POST,
)


class IntelligencePreset(str, Enum):
    lowest_price = "lowest_price"
    highest_price = "highest_price"
    agent_choice = "agent_choice"


@dataclass(frozen = True)
class PresetChoices:
    chat: str | None = None
    copywriting: str | None = None
    reasoning: str | None = None
    vision: str | None = None
    hearing: str | None = None
    images_gen: str | None = None
    images_edit: str | None = None
    search: str | None = None
    embedding: str | None = None
    api_fiat_exchange: str | None = None
    api_crypto_exchange: str | None = None
    api_twitter: str | None = None
    deprecated: str | None = None

    def as_dict(self) -> dict[str, str]:
        return {
            k: v
            for k, v in {
                ToolType.chat.value: self.chat,
                ToolType.copywriting.value: self.copywriting,
                ToolType.reasoning.value: self.reasoning,
                ToolType.vision.value: self.vision,
                ToolType.hearing.value: self.hearing,
                ToolType.images_gen.value: self.images_gen,
                ToolType.images_edit.value: self.images_edit,
                ToolType.search.value: self.search,
                ToolType.embedding.value: self.embedding,
                ToolType.api_fiat_exchange.value: self.api_fiat_exchange,
                ToolType.api_crypto_exchange.value: self.api_crypto_exchange,
                ToolType.api_twitter.value: self.api_twitter,
                ToolType.deprecated.value: self.deprecated,
            }.items()
            if v is not None
        }


INTELLIGENCE_PRESETS: dict[IntelligencePreset, PresetChoices] = {

    IntelligencePreset.lowest_price: PresetChoices(
        chat = GPT_5_NANO.id,
        copywriting = GPT_5_NANO.id,
        reasoning = GPT_5_NANO.id,
        vision = GPT_4_1_NANO.id,
        hearing = WHISPER_1.id,
        images_gen = IMAGE_GEN_EDIT_SEEDREAM_4.id,
        images_edit = IMAGE_GEN_EDIT_SEEDREAM_4.id,
        search = SONAR.id,
        embedding = TEXT_EMBEDDING_3_SMALL.id,
        api_fiat_exchange = FIAT_CURRENCY_EXCHANGE.id,
        api_crypto_exchange = CRYPTO_CURRENCY_EXCHANGE.id,
        api_twitter = X_READ_POST.id,
    ),

    IntelligencePreset.highest_price: PresetChoices(
        chat = GPT_5_4_PRO.id,
        copywriting = GPT_5_4_PRO.id,
        reasoning = CLAUDE_4_6_OPUS.id,
        vision = GPT_5_2.id,
        hearing = GPT_4O_TRANSCRIBE.id,
        images_gen = IMAGE_GEN_EDIT_GOOGLE_NANO_BANANA_2.id,
        images_edit = IMAGE_GEN_EDIT_GOOGLE_NANO_BANANA_2.id,
        search = SONAR_REASONING_PRO.id,
        embedding = TEXT_EMBEDDING_5_LARGE.id,
        api_fiat_exchange = FIAT_CURRENCY_EXCHANGE.id,
        api_crypto_exchange = CRYPTO_CURRENCY_EXCHANGE.id,
        api_twitter = X_READ_POST.id,
    ),

    IntelligencePreset.agent_choice: PresetChoices(
        chat = GPT_5_4.id,
        copywriting = GPT_5_4.id,
        reasoning = CLAUDE_4_6_SONNET.id,
        vision = GPT_5_2.id,
        hearing = GPT_4O_MINI_TRANSCRIBE.id,
        images_gen = IMAGE_GEN_EDIT_FLUX_2_PRO.id,
        images_edit = IMAGE_GEN_EDIT_FLUX_2_PRO.id,
        search = SONAR_PRO.id,
        embedding = TEXT_EMBEDDING_3_SMALL.id,
        api_fiat_exchange = FIAT_CURRENCY_EXCHANGE.id,
        api_crypto_exchange = CRYPTO_CURRENCY_EXCHANGE.id,
        api_twitter = X_READ_POST.id,
    ),

}


def get_all_presets() -> dict[str, dict[str, str]]:
    return {preset.value: choices.as_dict() for preset, choices in INTELLIGENCE_PRESETS.items()}
