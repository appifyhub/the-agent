import unittest
from datetime import datetime, timedelta

from db.crud.tools_cache import ToolsCacheCRUD
from db.schema.tools_cache import ToolsCacheSave
from db.sql_util import SQLUtil


class ToolsCacheCRUDTest(unittest.TestCase):
    sql: SQLUtil

    def setUp(self):
        self.sql = SQLUtil()

    def tearDown(self):
        self.sql.end_session()

    def test_create_tools_cache(self):
        tools_cache_data = ToolsCacheSave(
            key = "tool1",
            value = "some_value",
            expires_at = datetime.now() + timedelta(days = 1),
        )

        tools_cache = self.sql.tools_cache_crud().create(tools_cache_data)

        self.assertEqual(tools_cache.key, tools_cache_data.key)
        self.assertEqual(tools_cache.value, tools_cache_data.value)
        self.assertEqual(tools_cache.expires_at, tools_cache_data.expires_at)

    def test_get_tools_cache(self):
        tools_cache_data = ToolsCacheSave(
            key = "tool1",
            value = "some_value",
            expires_at = datetime.now() + timedelta(days = 1),
        )
        created_tools_cache = self.sql.tools_cache_crud().create(tools_cache_data)

        fetched_tools_cache = self.sql.tools_cache_crud().get(created_tools_cache.key)

        self.assertEqual(fetched_tools_cache.key, created_tools_cache.key)

    def test_get_all_tools_caches(self):
        tools_caches = [
            self.sql.tools_cache_crud().create(
                ToolsCacheSave(key = "tool1", value = "value1", expires_at = datetime.now() + timedelta(days = 1))
            ),
            self.sql.tools_cache_crud().create(
                ToolsCacheSave(key = "tool2", value = "value2", expires_at = datetime.now() + timedelta(days = 1))
            ),
        ]

        fetched_tools_caches = self.sql.tools_cache_crud().get_all()

        self.assertEqual(len(fetched_tools_caches), len(tools_caches))
        for i in range(len(tools_caches)):
            self.assertEqual(fetched_tools_caches[i].key, tools_caches[i].key)

    def test_update_tools_cache(self):
        tools_cache_data = ToolsCacheSave(
            key = "tool1",
            value = "some_value",
            expires_at = datetime.now() + timedelta(days = 1),
        )
        created_tools_cache = self.sql.tools_cache_crud().create(tools_cache_data)

        update_data = ToolsCacheSave(
            key = created_tools_cache.key,
            value = "new_value",
            expires_at = datetime.now() + timedelta(days = 2),
        )
        updated_tools_cache = self.sql.tools_cache_crud().update(update_data)

        self.assertEqual(updated_tools_cache.key, created_tools_cache.key)
        self.assertEqual(updated_tools_cache.value, update_data.value)
        self.assertEqual(updated_tools_cache.expires_at, update_data.expires_at)

    def test_save_tools_cache(self):
        tools_cache_data = ToolsCacheSave(
            key = "tool1",
            value = "some_value",
            expires_at = datetime.now() + timedelta(days = 1),
        )

        # First, save should create the record
        saved_tools_cache = self.sql.tools_cache_crud().save(tools_cache_data)
        self.assertIsNotNone(saved_tools_cache)
        self.assertEqual(saved_tools_cache.key, tools_cache_data.key)
        self.assertEqual(saved_tools_cache.value, tools_cache_data.value)
        self.assertEqual(saved_tools_cache.expires_at, tools_cache_data.expires_at)

        # Now, save should update the existing record
        update_data = ToolsCacheSave(
            key = saved_tools_cache.key,
            value = "new_value",
            expires_at = datetime.now() + timedelta(days = 2),
        )
        updated_tools_cache = self.sql.tools_cache_crud().save(update_data)
        self.assertIsNotNone(updated_tools_cache)
        self.assertEqual(updated_tools_cache.key, saved_tools_cache.key)
        self.assertEqual(updated_tools_cache.value, update_data.value)
        self.assertEqual(updated_tools_cache.expires_at, update_data.expires_at)

    def test_delete_tools_cache(self):
        tools_cache_data = ToolsCacheSave(
            key = "tool1",
            value = "some_value",
            expires_at = datetime.now() + timedelta(days = 1),
        )
        created_tools_cache = self.sql.tools_cache_crud().create(tools_cache_data)

        deleted_tools_cache = self.sql.tools_cache_crud().delete(created_tools_cache.key)

        self.assertEqual(deleted_tools_cache.key, created_tools_cache.key)
        self.assertIsNone(self.sql.tools_cache_crud().get(created_tools_cache.key))

    def test_delete_expired_tools_cache(self):
        # Creating tools cache entries with varying expiration times
        tools_cache_not_expired = self.sql.tools_cache_crud().create(
            ToolsCacheSave(key = "tool1", value = "value1", expires_at = datetime.now() + timedelta(days = 1))
        )
        tools_cache_expired = self.sql.tools_cache_crud().create(
            ToolsCacheSave(key = "tool2", value = "value2", expires_at = datetime.now() - timedelta(days = 1))
        )

        # Deleting expired cache entries
        count_deleted = self.sql.tools_cache_crud().delete_expired()
        self.assertEqual(count_deleted, 1)

        # Asserting non-expired entry still exists
        fetched_non_expired = self.sql.tools_cache_crud().get(tools_cache_not_expired.key)
        self.assertIsNotNone(fetched_non_expired)

        # Asserting expired entry does not exist
        fetched_expired = self.sql.tools_cache_crud().get(tools_cache_expired.key)
        self.assertIsNone(fetched_expired)

    def test_create_key(self):
        key = ToolsCacheCRUD.create_key("prefix", "identifier")
        self.assertEqual(key, "3fffc53e8c62753274ae6ff244f2f4a4")
