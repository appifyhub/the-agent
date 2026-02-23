from datetime import datetime

from di.di import DI
from features.accounting.usage.usage_aggregates import UsageAggregates
from features.accounting.usage.usage_record import UsageRecord
from util import log
from util.error_codes import INVALID_LIMIT
from util.errors import ValidationError


class UsageController:

    __di: DI

    def __init__(self, di: DI):
        self.__di = di

    def fetch_usage_records(
        self,
        user_id_hex: str,
        skip: int = 0,
        limit: int = 50,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        exclude_self: bool = False,
        include_sponsored: bool = False,
        tool_id: str | None = None,
        purpose: str | None = None,
        provider_id: str | None = None,
    ) -> list[UsageRecord]:
        if limit > 100:
            raise ValidationError("limit cannot exceed 100", INVALID_LIMIT)
        log.d(f"Fetching usage records for user '{user_id_hex}'")
        user = self.__di.authorization_service.authorize_for_user(self.__di.invoker, user_id_hex)
        return self.__di.usage_record_repo.get_by_user(
            user.id,
            skip = skip,
            limit = limit,
            start_date = start_date,
            end_date = end_date,
            exclude_self = exclude_self,
            include_sponsored = include_sponsored,
            tool_id = tool_id,
            purpose = purpose,
            provider_id = provider_id,
        )

    def fetch_usage_aggregates(
        self,
        user_id_hex: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        exclude_self: bool = False,
        include_sponsored: bool = False,
        tool_id: str | None = None,
        purpose: str | None = None,
        provider_id: str | None = None,
    ) -> UsageAggregates:
        log.d(f"Fetching usage aggregates for user '{user_id_hex}'")
        user = self.__di.authorization_service.authorize_for_user(self.__di.invoker, user_id_hex)
        return self.__di.usage_record_repo.get_aggregates_by_user(
            user.id,
            start_date = start_date,
            end_date = end_date,
            exclude_self = exclude_self,
            include_sponsored = include_sponsored,
            tool_id = tool_id,
            purpose = purpose,
            provider_id = provider_id,
        )
