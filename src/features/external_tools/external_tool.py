from dataclasses import dataclass
from enum import Enum


@dataclass(frozen = True)
class CostEstimate:
    """All costs are in credits."""
    input_1m_tokens: int | None = None
    output_1m_tokens: int | None = None
    search_1m_tokens: int | None = None
    image_1k: int | None = None
    image_2k: int | None = None
    image_4k: int | None = None
    api_call: int | None = None
    second_of_runtime: float | None = None


@dataclass(frozen = True)
class ExternalToolProvider:
    id: str
    name: str
    token_management_url: str
    token_format: str
    tools: list[str]

    def __hash__(self) -> int:
        return hash(self.id)


# in sync with db.model.user.UserDB
class ToolType(str, Enum):
    chat = "chat"  # core chat models
    reasoning = "reasoning"  # reasoning models
    copywriting = "copywriting"  # cleanup models
    vision = "vision"  # vision features
    hearing = "hearing"  # hearing features
    images_gen = "images_gen"  # image generation
    images_edit = "images_edit"  # image editing
    search = "search"  # web search features
    embedding = "embedding"  # embedding models
    api_fiat_exchange = "api_fiat_exchange"  # fiat exchange API
    api_crypto_exchange = "api_crypto_exchange"  # crypto exchange API
    api_twitter = "api_twitter"  # X (Twitter) API


@dataclass(frozen = True)
class ExternalTool:
    id: str
    name: str
    provider: ExternalToolProvider
    types: list[ToolType]
    cost_estimate: CostEstimate

    def __hash__(self) -> int:
        return hash(self.id)
