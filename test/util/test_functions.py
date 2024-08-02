import unittest
from datetime import date
from uuid import UUID

from db.schema.user import User
from util.config import config
from util.functions import is_the_agent


class FunctionsTest(unittest.TestCase):

    def test_is_the_agent_true(self):
        config.telegram_bot_username = "the_new_agent"
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "the_new_agent",
        )
        self.assertTrue(is_the_agent(user))

    def test_is_the_agent_false(self):
        config.telegram_bot_username = "the_not_agent"
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "the_new_agent",
        )
        self.assertFalse(is_the_agent(user))

    def test_is_the_agent_none(self):
        self.assertFalse(is_the_agent(None))
