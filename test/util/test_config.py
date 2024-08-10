import os
import unittest
from typing import AnyStr

from util.config import Config


class ConfigTest(unittest.TestCase):
    original_env: dict[AnyStr, AnyStr]

    def setUp(self):
        self.original_env = os.environ.copy()
        os.environ.clear()
        Config._instances = {}

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)
        Config._instances = {}

    def test_default_config(self):
        config = Config()

        self.assertEqual(config.verbose, False)
        self.assertEqual(config.web_retries, 3)
        self.assertEqual(config.web_retry_delay_s, 1)
        self.assertEqual(config.web_timeout_s, 10)
        self.assertEqual(config.max_invites_per_user, 2)
        self.assertEqual(config.website_url, "https://the-agent.appifyhub.com")
        self.assertTrue(config.api_key)  # Check if API key is generated
        self.assertEqual(config.db_url, "postgresql://root:root@localhost:5432/agent")
        self.assertEqual(config.telegram_bot_username, "the_agent")
        self.assertEqual(config.telegram_bot_name, "The Agent")
        self.assertEqual(config.telegram_bot_token, "invalid")
        self.assertEqual(config.telegram_api_base_url, "https://api.telegram.org")
        self.assertEqual(config.chat_history_depth, 30)
        self.assertEqual(config.anthropic_token, "invalid")
        self.assertEqual(config.open_ai_token, "invalid")

    def test_custom_config(self):
        os.environ["VERBOSE"] = "true"
        os.environ["WEB_RETRIES"] = "5"
        os.environ["WEB_RETRY_DELAY_S"] = "2"
        os.environ["WEB_TIMEOUT_S"] = "20"
        os.environ["MAX_INVITES_PER_USER"] = "5"
        os.environ["WEBSITE_URL"] = "https://new.the-agent.appifyhub.com"
        os.environ["POSTGRES_USER"] = "admin"
        os.environ["POSTGRES_PASS"] = "admin123"
        os.environ["POSTGRES_HOST"] = "db.example.com"
        os.environ["POSTGRES_DB"] = "test_db"
        os.environ["API_KEY"] = "1111-2222-3333-4444"
        os.environ["TELEGRAM_BOT_USERNAME"] = "the_new_agent"
        os.environ["TELEGRAM_BOT_NAME"] = "The New Agent"
        os.environ["TELEGRAM_BOT_TOKEN"] = "id:sha"
        os.environ["TELEGRAM_API_BASE_URL"] = "https://new.api.telegram.org"
        os.environ["CHAT_HISTORY_DEPTH"] = "10"
        os.environ["ANTHROPIC_TOKEN"] = "sk-a-valid"
        os.environ["OPEN_AI_TOKEN"] = "sk-o-valid"

        config = Config()

        self.assertEqual(config.verbose, True)
        self.assertEqual(config.web_retries, 5)
        self.assertEqual(config.web_retry_delay_s, 2)
        self.assertEqual(config.web_timeout_s, 20)
        self.assertEqual(config.max_invites_per_user, 5)
        self.assertEqual(config.website_url, "https://new.the-agent.appifyhub.com")
        self.assertEqual(config.db_url, "postgresql://admin:admin123@db.example.com:5432/test_db")
        self.assertEqual(config.api_key, "1111-2222-3333-4444")
        self.assertEqual(config.telegram_bot_username, "the_new_agent")
        self.assertEqual(config.telegram_bot_name, "The New Agent")
        self.assertEqual(config.telegram_bot_token, "id:sha")
        self.assertEqual(config.telegram_api_base_url, "https://new.api.telegram.org")
        self.assertEqual(config.chat_history_depth, 10)
        self.assertEqual(config.anthropic_token, "sk-a-valid")
        self.assertEqual(config.open_ai_token, "sk-o-valid")
