from uuid import UUID

from sqlalchemy.orm import Session

from db.model.price_alert import PriceAlertDB
from db.schema.price_alert import PriceAlertSave


class PriceAlertCRUD:

    _db: Session

    def __init__(self, db: Session):
        self._db = db

    def get(self, chat_id: UUID, base_currency: str, desired_currency: str) -> PriceAlertDB | None:
        return self._db.query(PriceAlertDB).filter(
            PriceAlertDB.chat_id == chat_id,
            PriceAlertDB.base_currency == base_currency,
            PriceAlertDB.desired_currency == desired_currency,
        ).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[PriceAlertDB]:
        # noinspection PyTypeChecker
        return self._db.query(PriceAlertDB).offset(skip).limit(limit).all()

    def get_alerts_by_chat(self, chat_id: UUID) -> list[PriceAlertDB]:
        # noinspection PyTypeChecker
        return self._db.query(PriceAlertDB).filter(
            PriceAlertDB.chat_id == chat_id,
        ).all()

    def create(self, create_data: PriceAlertSave) -> PriceAlertDB:
        price_alert = PriceAlertDB(**create_data.model_dump())
        self._db.add(price_alert)
        self._db.commit()
        self._db.refresh(price_alert)
        return price_alert

    def update(self, update_data: PriceAlertSave) -> PriceAlertDB | None:
        price_alert = self.get(update_data.chat_id, update_data.base_currency, update_data.desired_currency)
        if price_alert:
            for key, value in update_data.model_dump().items():
                setattr(price_alert, key, value)
            self._db.commit()
            self._db.refresh(price_alert)
        return price_alert

    def save(self, data: PriceAlertSave) -> PriceAlertDB:
        updated_alert = self.update(data)
        if updated_alert:
            return updated_alert
        return self.create(data)

    def delete(self, chat_id: UUID, base_currency: str, desired_currency: str) -> PriceAlertDB | None:
        price_alert = self.get(chat_id, base_currency, desired_currency)
        if price_alert:
            self._db.delete(price_alert)
            self._db.commit()
        return price_alert
