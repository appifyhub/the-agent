from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from features.external_tools.external_tool import ExternalTool, ToolType


@dataclass(kw_only = True)
class UsageRecord:
    # core properties
    user_id: UUID
    chat_id: UUID | None = None
    tool: ExternalTool
    tool_purpose: ToolType
    timestamp: datetime = field(default_factory = lambda: datetime.now(timezone.utc))
    runtime_seconds: float
    remote_runtime_seconds: float | None = None
    # cost properties
    model_cost_credits: float
    remote_runtime_cost_credits: float
    api_call_cost_credits: float
    maintenance_fee_credits: float
    total_cost_credits: float
    # token-based properties
    input_tokens: int | None = None
    output_tokens: int | None = None
    search_tokens: int | None = None
    total_tokens: int | None = None
    # image-related properties
    image_count: int | None = None
    image_size: str | None = None
