from dataclasses import dataclass


@dataclass(kw_only = True)
class ProductAggregateStats:
    record_count: int
    total_cost_cents: int
    total_net_cost_cents: int


@dataclass(kw_only = True)
class ProductInfo:
    id: str
    name: str


@dataclass(kw_only = True)
class PurchaseAggregates:
    total_purchase_count: int
    total_cost_cents: int
    total_net_cost_cents: int
    by_product: dict[str, ProductAggregateStats]
    all_products_used: list[ProductInfo]
