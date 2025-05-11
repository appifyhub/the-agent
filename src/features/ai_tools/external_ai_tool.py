from dataclasses import dataclass
from enum import Enum


@dataclass(frozen = True)
class ToolProvider:
    id: str
    name: str
    token_management_url: str
    token_format: str
    tools: list[str]


@dataclass(frozen = True)
class ToolType(Enum):
    llm = "llm"  # core generative text models
    vision = "vision"  # vision features
    hearing = "hearing"  # hearing features
    images = "images"  # image-gen and editing
    search = "search"  # web search features
    embedding = "embedding"  # embedding models
    api = "api"  # networking and APIs


@dataclass(frozen = True)
class ExternalAiTool:
    id: str
    name: str
    provider: ToolProvider
    types: list[ToolType]
