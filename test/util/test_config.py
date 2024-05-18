import os
import unittest

from util.config import Config


class ConfigTest(unittest.TestCase):

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
        self.assertTrue(config.api_key)  # Check if API key is generated
        self.assertEqual(config.db_url, "postgresql://root:root@localhost:5432/agent")

    def test_custom_config(self):
        os.environ["VERBOSE"] = "true"
        os.environ["WEB_RETRIES"] = "5"
        os.environ["WEB_RETRY_DELAY_S"] = "2"
        os.environ["WEB_TIMEOUT_S"] = "20"
        os.environ["MAX_INVITES_PER_USER"] = "5"
        os.environ["POSTGRES_USER"] = "admin"
        os.environ["POSTGRES_PASS"] = "admin123"
        os.environ["POSTGRES_HOST"] = "db.example.com"
        os.environ["POSTGRES_DB"] = "test_db"

        config = Config()

        self.assertEqual(config.verbose, True)
        self.assertEqual(config.web_retries, 5)
        self.assertEqual(config.web_retry_delay_s, 2)
        self.assertEqual(config.web_timeout_s, 20)
        self.assertEqual(config.max_invites_per_user, 5)
        self.assertEqual(config.db_url, "postgresql://admin:admin123@db.example.com:5432/test_db")
