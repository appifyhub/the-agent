from dataclasses import dataclass
from enum import Enum


@dataclass(frozen = True)
class ExternalToolProvider:
    id: str
    name: str
    token_management_url: str
    token_format: str
    tools: list[str]


# in sync with db.model.user.UserDB
class ToolType(str, Enum):
    chat = "chat"  # core chat models
    reasoning = "reasoning"  # reasoning models
    copywriting = "copywriting"  # cleanup models
    vision = "vision"  # vision features
    hearing = "hearing"  # hearing features
    images_gen = "images_gen"  # image generation
    images_edit = "images_edit"  # image editing
    images_restoration = "images_restoration"  # image restoration
    images_inpainting = "images_inpainting"  # image inpainting
    images_background_removal = "images_background_removal"  # image background removal
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
