from sqlalchemy import Column, String, Float, DateTime, ForeignKey, PrimaryKeyConstraint, Integer

from db.model.base import BaseModel


class PriceAlertDB(BaseModel):
    __tablename__ = "price_alerts"

    chat_id = Column(String, ForeignKey("chat_configs.chat_id"), nullable = False)
    base_currency = Column(String, nullable = False)
    desired_currency = Column(String, nullable = False)
    threshold_percent = Column(Integer, nullable = False)
    last_price = Column(Float, nullable = False)
    last_price_time = Column(DateTime, nullable = False)

    __table_args__ = (
        PrimaryKeyConstraint(chat_id, base_currency, desired_currency, name = "pk_price_alert"),
    )
