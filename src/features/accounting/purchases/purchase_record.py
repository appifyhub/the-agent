from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(kw_only = True)
class PurchaseRecord:
    id: UUID
    user_id: UUID | None = None
    seller_id: str
    sale_id: str
    sale_timestamp: datetime
    price: int
    product_id: str
    product_name: str
    product_permalink: str
    short_product_id: str
    license_key: str | None = None
    quantity: int
    gumroad_fee: int = 0
    affiliate_credit_amount_cents: int = 0
    discover_fee_charge: bool = False
    url_params: dict | None = None
    custom_fields: dict | None = None
    test: bool = False
    is_preorder_authorization: bool = False
    refunded: bool = False
