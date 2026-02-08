from typing import Any

from pydantic import BaseModel, field_validator


class GumroadPingPayload(BaseModel):
    seller_id: str
    sale_id: str
    sale_timestamp: str
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

    @field_validator(
        "test",
        "is_preorder_authorization",
        "refunded",
        "discover_fee_charge",
        mode = "before",
    )
    @classmethod
    def coerce_bool(cls, v: Any) -> bool:
        if isinstance(v, str):
            return v.lower() == "true"
        return bool(v)

    @field_validator(
        "price",
        "quantity",
        "gumroad_fee",
        "affiliate_credit_amount_cents",
        mode = "before",
    )
    @classmethod
    def coerce_int(cls, v: Any) -> int:
        if isinstance(v, str):
            return int(v)
        return int(v)
