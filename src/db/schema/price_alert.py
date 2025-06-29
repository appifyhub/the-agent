from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PriceAlertBase(BaseModel):
    chat_id: str
    owner_id: UUID
    base_currency: str
    desired_currency: str
    threshold_percent: int
    last_price: float
    last_price_time: datetime = datetime.now()


class PriceAlertSave(PriceAlertBase):
    pass


class PriceAlert(PriceAlertBase):
    model_config = ConfigDict(from_attributes = True)
