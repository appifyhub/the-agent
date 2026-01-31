from dataclasses import dataclass


@dataclass(kw_only = True)
class AggregateStats:
    record_count: int
    total_cost: float


@dataclass(kw_only = True)
class ToolInfo:
    id: str
    name: str


@dataclass(kw_only = True)
class ProviderInfo:
    id: str
    name: str


@dataclass(kw_only = True)
class UsageAggregates:
    total_records: int
    total_cost_credits: float
    total_runtime_seconds: float
    by_tool: dict[str, AggregateStats]
    by_purpose: dict[str, AggregateStats]
    by_provider: dict[str, AggregateStats]
    all_tools_used: list[ToolInfo]
    all_purposes_used: list[str]
    all_providers_used: list[ProviderInfo]
