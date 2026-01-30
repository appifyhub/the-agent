from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Query, Session

from db.model.sponsorship import SponsorshipDB
from db.model.usage_record import UsageRecordDB
from features.accounting.repo.usage_record_mapper import db, domain
from features.accounting.stats.usage_aggregates import AggregateStats, ProviderInfo, UsageAggregates
from features.accounting.stats.usage_record import UsageRecord


class UsageRecordRepository:

    _db: Session

    def __init__(self, db: Session):
        self._db = db

    def get(self, record_id: UUID) -> UsageRecord | None:
        db_model = self._db.query(UsageRecordDB).filter(UsageRecordDB.id == record_id).first()
        return domain(db_model)

    def create(self, record: UsageRecord) -> UsageRecord:
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
        exclude_self: bool = False,
        include_sponsored: bool = False,
    ) -> list[UsageRecord]:
        base_query = self._build_user_query(user_id, start_date, end_date, exclude_self, include_sponsored)
        db_models = base_query.order_by(UsageRecordDB.timestamp.desc()).offset(skip).limit(limit).all()
        return [domain(db_model) for db_model in db_models]

    def get_aggregates_by_user(
        self,
        user_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        exclude_self: bool = False,
        include_sponsored: bool = False,
    ) -> UsageAggregates:
        base_query = self._build_user_query(user_id, start_date, end_date, exclude_self, include_sponsored)
        subquery = base_query.subquery()

        # first we pull the totals
        total_records = int(self._db.query(func.count(subquery.c.id)).scalar() or 0)
        total_cost = float(self._db.query(func.sum(subquery.c.total_cost_credits)).scalar() or 0.0)

        # here we pull the per-tool aggregated stats
        by_tool: dict[str, AggregateStats] = {}
        tool_stats = self._db.query(
            subquery.c.tool_name,
            func.count(subquery.c.id).label("count"),
            func.sum(subquery.c.total_cost_credits).label("total_cost"),
        ).group_by(subquery.c.tool_name).all()
        for tool_name, count, total_cost_val in tool_stats:
            by_tool[str(tool_name)] = AggregateStats(
                record_count = int(count),
                total_cost = float(total_cost_val or 0),
            )

        # here we pull the per-purpose aggregated stats
        by_purpose: dict[str, AggregateStats] = {}
        purpose_stats = self._db.query(
            subquery.c.purpose,
            func.count(subquery.c.id).label("count"),
            func.sum(subquery.c.total_cost_credits).label("total_cost"),
        ).group_by(subquery.c.purpose).all()
        for purpose, count, total_cost_val in purpose_stats:
            by_purpose[str(purpose)] = AggregateStats(
                record_count = int(count),
                total_cost = float(total_cost_val or 0),
            )

        # here we pull the per-provider aggregated stats
        by_provider: dict[str, AggregateStats] = {}
        provider_stats = self._db.query(
            subquery.c.provider_name,
            func.count(subquery.c.id).label("count"),
            func.sum(subquery.c.total_cost_credits).label("total_cost"),
        ).group_by(subquery.c.provider_name).all()
        for provider_name, count, total_cost_val in provider_stats:
            by_provider[str(provider_name)] = AggregateStats(
                record_count = int(count),
                total_cost = float(total_cost_val or 0),
            )

        # we can manually group the lists of tools and purposes
        all_tools_used = sorted(by_tool.keys())
        all_purposes_used = sorted(by_purpose.keys())
        # providers need both ID and Name, so we need to query for distinct pairs
        all_providers_used = self._db.query(
            subquery.c.provider_id,
            subquery.c.provider_name,
        ).distinct().all()
        all_providers_used = sorted(
            [ProviderInfo(id = str(row[0]), name = str(row[1])) for row in all_providers_used],
            key = lambda x: x.name,
        )

        return UsageAggregates(
            total_records = total_records,
            total_cost_credits = total_cost,
            by_tool = by_tool,
            by_purpose = by_purpose,
            by_provider = by_provider,
            all_tools_used = all_tools_used,
            all_purposes_used = all_purposes_used,
            all_providers_used = all_providers_used,
        )

    def _build_user_query(
        self,
        user_id: UUID,
        start_date: datetime | None,
        end_date: datetime | None,
        exclude_self: bool,
        include_sponsored: bool,
    ) -> Query:
        if not include_sponsored:
            base_query = self._db.query(UsageRecordDB).filter(UsageRecordDB.user_id == user_id)
        else:
            sponsored_user_ids = self._db.query(SponsorshipDB.receiver_id).filter(
                SponsorshipDB.sponsor_id == user_id,
            )
            if exclude_self:
                base_query = self._db.query(UsageRecordDB).filter(
                    UsageRecordDB.user_id.in_(sponsored_user_ids),
                )
            else:
                base_query = self._db.query(UsageRecordDB).filter(
                    or_(
                        UsageRecordDB.user_id == user_id,
                        UsageRecordDB.user_id.in_(sponsored_user_ids),
                    ),
                )

        if start_date is not None:
            base_query = base_query.filter(UsageRecordDB.timestamp >= start_date)

        if end_date is not None:
            base_query = base_query.filter(UsageRecordDB.timestamp <= end_date)

        return base_query
