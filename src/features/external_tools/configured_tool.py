from dataclasses import dataclass
from uuid import UUID

from pydantic import SecretStr

from features.external_tools.external_tool import ExternalTool, ToolType


@dataclass(frozen = True)
class ConfiguredTool:
    definition: ExternalTool
    token: SecretStr
    purpose: ToolType
    payer_id: UUID
    uses_credits: bool
