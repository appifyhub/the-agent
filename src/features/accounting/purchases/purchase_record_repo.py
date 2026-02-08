from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.model.purchase_record import PurchaseRecordDB
from features.accounting.purchases.purchase_aggregates import (
    ProductAggregateStats,
    ProductInfo,
    PurchaseAggregates,
)
from features.accounting.purchases.purchase_record import PurchaseRecord
from features.accounting.purchases.purchase_record_mapper import db, domain


class PurchaseRecordRepository:

    _db: Session

    def __init__(self, db_session: Session):
        self._db = db_session

    def save(self, record: PurchaseRecord) -> PurchaseRecord:
        existing = self._db.query(PurchaseRecordDB).filter(
            PurchaseRecordDB.id == record.id,
        ).first()

        if existing is None:
            existing = self._db.query(PurchaseRecordDB).filter(
                PurchaseRecordDB.sale_id == record.sale_id,
            ).first()

        if existing:
            if record.user_id is not None:
                existing.user_id = record.user_id
            if record.license_key is not None:
                existing.license_key = record.license_key
            if record.url_params is not None:
                existing.url_params = record.url_params
            if record.custom_fields is not None:
                existing.custom_fields = record.custom_fields
            existing.seller_id = record.seller_id
            existing.sale_timestamp = record.sale_timestamp
            existing.price = record.price
            existing.product_id = record.product_id
            existing.product_name = record.product_name
            existing.product_permalink = record.product_permalink
            existing.short_product_id = record.short_product_id
            existing.quantity = record.quantity
            existing.gumroad_fee = record.gumroad_fee
            existing.affiliate_credit_amount_cents = record.affiliate_credit_amount_cents
            existing.discover_fee_charge = record.discover_fee_charge
            existing.test = record.test
            existing.is_preorder_authorization = record.is_preorder_authorization
            existing.refunded = record.refunded
            self._db.commit()
            self._db.refresh(existing)
            return domain(existing)

        db_model = db(record)
        self._db.add(db_model)
        self._db.commit()
        self._db.refresh(db_model)
        return domain(db_model)

    def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        product_id: str | None = None,
    ) -> list[PurchaseRecord]:
        query = self._db.query(PurchaseRecordDB).filter(PurchaseRecordDB.user_id == user_id)

        if start_date is not None:
            query = query.filter(PurchaseRecordDB.sale_timestamp >= start_date)
        if end_date is not None:
            query = query.filter(PurchaseRecordDB.sale_timestamp <= end_date)
        if product_id:
            query = query.filter(PurchaseRecordDB.product_id == product_id)

        db_models = query.order_by(PurchaseRecordDB.sale_timestamp.desc()).offset(skip).limit(limit).all()
        return [domain(db_model) for db_model in db_models]

    def get_aggregates_by_user(
        self,
        user_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        product_id: str | None = None,
    ) -> PurchaseAggregates:
        unfiltered_query = self._db.query(PurchaseRecordDB).filter(PurchaseRecordDB.user_id == user_id)
        if start_date is not None:
            unfiltered_query = unfiltered_query.filter(PurchaseRecordDB.sale_timestamp >= start_date)
        if end_date is not None:
            unfiltered_query = unfiltered_query.filter(PurchaseRecordDB.sale_timestamp <= end_date)
        unfiltered_subquery = unfiltered_query.subquery()

        filtered_query = self._db.query(PurchaseRecordDB).filter(PurchaseRecordDB.user_id == user_id)
        if start_date is not None:
            filtered_query = filtered_query.filter(PurchaseRecordDB.sale_timestamp >= start_date)
        if end_date is not None:
            filtered_query = filtered_query.filter(PurchaseRecordDB.sale_timestamp <= end_date)
        if product_id:
            filtered_query = filtered_query.filter(PurchaseRecordDB.product_id == product_id)
        filtered_subquery = filtered_query.subquery()

        total_purchase_count = int(self._db.query(func.count(filtered_subquery.c.id)).scalar() or 0)
        total_cost_cents = int(self._db.query(func.sum(filtered_subquery.c.price)).scalar() or 0)

        net_cost_query = self._db.query(
            func.sum(
                filtered_subquery.c.price
                - filtered_subquery.c.gumroad_fee
                - filtered_subquery.c.affiliate_credit_amount_cents,
            ),
        ).scalar()
        total_net_cost_cents = int(net_cost_query or 0)

        by_product: dict[str, ProductAggregateStats] = {}
        product_stats = self._db.query(
            filtered_subquery.c.product_id,
            func.count(filtered_subquery.c.id).label("count"),
            func.sum(filtered_subquery.c.price).label("total_cost"),
            func.sum(
                filtered_subquery.c.price
                - filtered_subquery.c.gumroad_fee
                - filtered_subquery.c.affiliate_credit_amount_cents,
            ).label("total_net_cost"),
        ).group_by(filtered_subquery.c.product_id).all()

        for prod_id, count, total_cost, total_net_cost in product_stats:
            by_product[str(prod_id)] = ProductAggregateStats(
                record_count = int(count),
                total_cost_cents = int(total_cost or 0),
                total_net_cost_cents = int(total_net_cost or 0),
            )

        all_products_db = self._db.query(
            unfiltered_subquery.c.product_id,
            unfiltered_subquery.c.product_name,
        ).distinct().all()
        all_products_used = sorted(
            [ProductInfo(id = str(row[0]), name = str(row[1])) for row in all_products_db],
            key = lambda x: x.name,
        )

        return PurchaseAggregates(
            total_purchase_count = total_purchase_count,
            total_cost_cents = total_cost_cents,
            total_net_cost_cents = total_net_cost_cents,
            by_product = by_product,
            all_products_used = all_products_used,
        )

    def bind_license_key_to_user(self, license_key: str, user_id: UUID) -> PurchaseRecord:
        db_model = self._db.query(PurchaseRecordDB).filter(
            PurchaseRecordDB.license_key == license_key,
        ).first()

        if db_model is None:
            raise ValueError(f"License key {license_key} not found")

        if db_model.refunded:
            raise ValueError(f"License key {license_key} is refunded and cannot be bound")

        if db_model.test:
            raise ValueError(f"License key {license_key} is from a test order and cannot be bound")

        if db_model.is_preorder_authorization:
            raise ValueError(f"License key {license_key} is from a preorder and cannot be bound")

        if db_model.user_id is None:
            db_model.user_id = user_id
            self._db.commit()
            self._db.refresh(db_model)
            return domain(db_model)
        else:
            raise ValueError(f"License key {license_key} is already bound to user {db_model.user_id}")
