from dataclasses import dataclass
from enum import Enum


@dataclass(frozen = True)
class ExternalToolProvider:
    id: str
    name: str
    token_management_url: str
    token_format: str
    tools: list[str]


class ToolType(str, Enum):
    llm = "llm"  # core generative text models
    vision = "vision"  # vision features
    hearing = "hearing"  # hearing features
    images = "images"  # image-gen and editing
    search = "search"  # web search features
    embedding = "embedding"  # embedding models
    api = "api"  # networking and APIs


@dataclass(frozen = True)
class ExternalTool:
    id: str
    name: str
    provider: ExternalToolProvider
    types: list[ToolType]
