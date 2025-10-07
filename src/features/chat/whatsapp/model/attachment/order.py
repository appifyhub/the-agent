from pydantic import BaseModel


class ProductItem(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#order-messages"""
    product_retailer_id: str
    quantity: int
    item_price: str
    currency: str


class Order(BaseModel):
    """https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/reference/messages#order-messages"""
    catalog_id: str
    product_items: list[ProductItem]
    text: str | None = None
