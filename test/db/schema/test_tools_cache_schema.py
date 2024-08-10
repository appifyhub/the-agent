import unittest
from datetime import datetime, timedelta

from db.schema.tools_cache import ToolsCacheBase


class ToolsCacheTest(unittest.TestCase):

    def test_is_expired_with_no_expiration(self):
        tools_cache = ToolsCacheBase(key = "key1", value = "value1")
        self.assertFalse(tools_cache.is_expired())

    def test_is_expired_with_future_expiration(self):
        future_date = datetime.now() + timedelta(days = 1)
        tools_cache = ToolsCacheBase(key = "key2", value = "value2", expires_at = future_date)
        self.assertFalse(tools_cache.is_expired())

    def test_is_expired_with_past_expiration(self):
        past_date = datetime.now() - timedelta(days = 1)
        tools_cache = ToolsCacheBase(key = "key3", value = "value3", expires_at = past_date)
        self.assertTrue(tools_cache.is_expired())
