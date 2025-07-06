from dataclasses import dataclass
from typing import List

from features.external_tools.external_tool import ExternalTool, ExternalToolProvider


@dataclass(frozen = True)
class ExternalToolProviderResponse:
    definition: ExternalToolProvider
    is_configured: bool


@dataclass(frozen = True)
class ExternalToolResponse:
    definition: ExternalTool
    is_configured: bool


@dataclass(frozen = True)
class ExternalToolsResponse:
    tools: List[ExternalToolResponse]
    providers: List[ExternalToolProviderResponse]
