import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from db.sql_util import SQLUtil

from db.model.usage_record import UsageRecordDB
from db.model.user import UserDB
from db.schema.sponsorship import SponsorshipSave
from db.schema.user import UserSave
from features.accounting.repo.usage_record_repo import UsageRecordRepository
from features.accounting.stats.usage_record import UsageRecord
from features.external_tools.external_tool import ToolType
from features.external_tools.external_tool_library import CLAUDE_3_5_HAIKU, GPT_4O


class UsageRecordRepositoryTest(unittest.TestCase):

    sql: SQLUtil
    repo: UsageRecordRepository
    user: UserDB

    def setUp(self):
        self.sql = SQLUtil()
        self.repo = self.sql.usage_record_repo()
        self.user = self.sql.user_crud().create(UserSave(connect_key = "TEST-KEY-1234"))

    def tearDown(self):
        self.sql.end_session()

    def _create_record(
        self,
        user_id = None,
        tool = GPT_4O,
        tool_purpose = ToolType.chat,
        total_cost_credits = 1.0,
        timestamp = None,
    ) -> UsageRecord:
        return UsageRecord(
            user_id = user_id or self.user.id,
            tool = tool,
            tool_purpose = tool_purpose,
            timestamp = timestamp or datetime.now(timezone.utc),
            model_cost_credits = 0,
            remote_runtime_cost_credits = 0,
            api_call_cost_credits = 0,
            maintenance_fee_credits = 0,
            total_cost_credits = total_cost_credits,
            runtime_seconds = 1.0,
        )

    def test_create(self):
        record = UsageRecord(
            user_id = self.user.id,
            tool = GPT_4O,
            tool_purpose = ToolType.vision,
            model_cost_credits = 0.5,
            remote_runtime_cost_credits = 0.1,
            api_call_cost_credits = 0.0,
            maintenance_fee_credits = 0.1,
            total_cost_credits = 0.7,
            runtime_seconds = 1.5,
            output_image_sizes = ["1024x1024"],
        )

        persisted = self.repo.create(record)

        self.assertIsNotNone(persisted)
        self.assertEqual(persisted.user_id, self.user.id)
        self.assertEqual(persisted.tool.id, record.tool.id)
        self.assertEqual(persisted.tool_purpose, ToolType.vision)
        self.assertEqual(persisted.total_cost_credits, 0.7)
        self.assertEqual(persisted.output_image_sizes, ["1024x1024"])

    def test_get(self):
        record = self._create_record()
        self.repo.create(record)

        db_record = self.sql.get_session().query(UsageRecordDB).filter(
            UsageRecordDB.user_id == self.user.id,
        ).first()

        fetched = self.repo.get(db_record.id)

        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.user_id, self.user.id)
        self.assertEqual(fetched.tool.id, record.tool.id)

    def test_get_nonexistent(self):
        fetched = self.repo.get(uuid4())
        self.assertIsNone(fetched)

    def test_get_by_user_pagination_limit(self):
        for _ in range(3):
            self.repo.create(self._create_record())

        records = self.repo.get_by_user(self.user.id, limit = 2)
        self.assertEqual(len(records), 2)

        records_all = self.repo.get_by_user(self.user.id, limit = 10)
        self.assertEqual(len(records_all), 3)

    def test_get_by_user_pagination_skip(self):
        for _ in range(5):
            self.repo.create(self._create_record())

        records = self.repo.get_by_user(self.user.id, skip = 2, limit = 10)
        self.assertEqual(len(records), 3)

    def test_get_by_user_start_date_filter(self):
        now = datetime.now(timezone.utc)
        self.repo.create(self._create_record(timestamp = now - timedelta(days = 2)))
        self.repo.create(self._create_record(timestamp = now))

        records = self.repo.get_by_user(self.user.id, start_date = now - timedelta(hours = 1))

        self.assertEqual(len(records), 1)

    def test_get_by_user_end_date_filter(self):
        now = datetime.now(timezone.utc)
        self.repo.create(self._create_record(timestamp = now - timedelta(days = 2)))
        self.repo.create(self._create_record(timestamp = now))

        records = self.repo.get_by_user(self.user.id, end_date = now - timedelta(days = 1))

        self.assertEqual(len(records), 1)

    def test_get_by_user_date_range_filter(self):
        now = datetime.now(timezone.utc)
        self.repo.create(self._create_record(timestamp = now - timedelta(days = 5)))
        self.repo.create(self._create_record(timestamp = now - timedelta(days = 2)))
        self.repo.create(self._create_record(timestamp = now))

        records = self.repo.get_by_user(
            self.user.id,
            start_date = now - timedelta(days = 3),
            end_date = now - timedelta(days = 1),
        )

        self.assertEqual(len(records), 1)

    def test_get_by_user_include_sponsored(self):
        sponsored_user = self.sql.user_crud().create(UserSave(connect_key = "SPONSORED-KEY"))
        self.sql.sponsorship_crud().create(SponsorshipSave(
            sponsor_id = self.user.id,
            receiver_id = sponsored_user.id,
        ))

        self.repo.create(self._create_record(total_cost_credits = 10))
        self.repo.create(self._create_record(user_id = sponsored_user.id, total_cost_credits = 20))

        records = self.repo.get_by_user(self.user.id, include_sponsored = True)

        self.assertEqual(len(records), 2)

    def test_get_by_user_exclude_self(self):
        sponsored_user = self.sql.user_crud().create(UserSave(connect_key = "SPONSORED-KEY"))
        self.sql.sponsorship_crud().create(SponsorshipSave(
            sponsor_id = self.user.id,
            receiver_id = sponsored_user.id,
        ))

        self.repo.create(self._create_record(total_cost_credits = 10))
        self.repo.create(self._create_record(user_id = sponsored_user.id, total_cost_credits = 20))

        records = self.repo.get_by_user(self.user.id, include_sponsored = True, exclude_self = True)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].user_id, sponsored_user.id)

    def test_get_aggregates_by_user(self):
        self.repo.create(self._create_record(
            tool = GPT_4O,
            tool_purpose = ToolType.chat,
            total_cost_credits = 10,
        ))
        self.repo.create(self._create_record(
            tool = GPT_4O,
            tool_purpose = ToolType.chat,
            total_cost_credits = 5,
        ))
        self.repo.create(self._create_record(
            tool = CLAUDE_3_5_HAIKU,
            tool_purpose = ToolType.images_gen,
            total_cost_credits = 20,
        ))

        stats = self.repo.get_aggregates_by_user(self.user.id)

        self.assertEqual(stats.total_records, 3)
        self.assertEqual(stats.total_cost_credits, 35.0)

        # by_tool
        self.assertEqual(len(stats.by_tool), 2)
        self.assertEqual(stats.by_tool[GPT_4O.name].record_count, 2)
        self.assertEqual(stats.by_tool[GPT_4O.name].total_cost, 15.0)
        self.assertEqual(stats.by_tool[CLAUDE_3_5_HAIKU.name].record_count, 1)
        self.assertEqual(stats.by_tool[CLAUDE_3_5_HAIKU.name].total_cost, 20.0)

        # by_purpose
        self.assertEqual(len(stats.by_purpose), 2)
        self.assertEqual(stats.by_purpose[ToolType.chat.value].record_count, 2)
        self.assertEqual(stats.by_purpose[ToolType.chat.value].total_cost, 15.0)
        self.assertEqual(stats.by_purpose[ToolType.images_gen.value].record_count, 1)
        self.assertEqual(stats.by_purpose[ToolType.images_gen.value].total_cost, 20.0)

        # by_provider
        self.assertEqual(len(stats.by_provider), 2)
        self.assertEqual(stats.by_provider[GPT_4O.provider.name].record_count, 2)
        self.assertEqual(stats.by_provider[GPT_4O.provider.name].total_cost, 15.0)
        self.assertEqual(stats.by_provider[CLAUDE_3_5_HAIKU.provider.name].record_count, 1)
        self.assertEqual(stats.by_provider[CLAUDE_3_5_HAIKU.provider.name].total_cost, 20.0)

        # all_*_used lists
        self.assertIn(GPT_4O.name, stats.all_tools_used)
        self.assertIn(CLAUDE_3_5_HAIKU.name, stats.all_tools_used)
        self.assertIn(ToolType.chat.value, stats.all_purposes_used)
        self.assertIn(ToolType.images_gen.value, stats.all_purposes_used)

    def test_get_aggregates_by_user_empty(self):
        stats = self.repo.get_aggregates_by_user(self.user.id)

        self.assertEqual(stats.total_records, 0)
        self.assertEqual(stats.total_cost_credits, 0.0)
        self.assertEqual(len(stats.by_tool), 0)
        self.assertEqual(len(stats.by_purpose), 0)
        self.assertEqual(len(stats.by_provider), 0)
        self.assertEqual(len(stats.all_tools_used), 0)
        self.assertEqual(len(stats.all_purposes_used), 0)
        self.assertEqual(len(stats.all_providers_used), 0)

    def test_get_aggregates_by_user_with_date_filter(self):
        now = datetime.now(timezone.utc)
        self.repo.create(self._create_record(
            timestamp = now - timedelta(days = 5),
            total_cost_credits = 100,
        ))
        self.repo.create(self._create_record(
            timestamp = now,
            total_cost_credits = 10,
        ))

        stats = self.repo.get_aggregates_by_user(
            self.user.id,
            start_date = now - timedelta(hours = 1),
        )

        self.assertEqual(stats.total_records, 1)
        self.assertEqual(stats.total_cost_credits, 10.0)

    def test_get_aggregates_by_user_include_sponsored(self):
        sponsored_user = self.sql.user_crud().create(UserSave(connect_key = "SPONSORED-KEY"))
        self.sql.sponsorship_crud().create(SponsorshipSave(
            sponsor_id = self.user.id,
            receiver_id = sponsored_user.id,
        ))

        self.repo.create(self._create_record(total_cost_credits = 10))
        self.repo.create(self._create_record(user_id = sponsored_user.id, total_cost_credits = 20))

        stats = self.repo.get_aggregates_by_user(self.user.id, include_sponsored = True)

        self.assertEqual(stats.total_records, 2)
        self.assertEqual(stats.total_cost_credits, 30.0)
