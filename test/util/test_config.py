import os
import unittest
from typing import AnyStr

from util.config import Config


class ConfigTest(unittest.TestCase):
    # noinspection PyTypeHints
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
        self.assertEqual(config.log_telegram_update, False)
        self.assertEqual(config.web_retries, 3)
        self.assertEqual(config.web_retry_delay_s, 1)
        self.assertEqual(config.web_timeout_s, 10)
        self.assertEqual(config.max_invites_per_user, 2)
        self.assertEqual(config.max_users, 100)
        self.assertEqual(config.website_url, "https://agent.appifyhub.com")
        self.assertTrue(config.api_key)  # Check if API key is generated
        self.assertEqual(config.parent_organization, "AppifyHub")
        self.assertEqual(config.db_url, "postgresql://root:root@localhost:5432/agent")
        self.assertEqual(config.telegram_bot_username, "the_agent")
        self.assertEqual(config.telegram_bot_name, "The Agent")
        self.assertEqual(config.telegram_bot_id, 1234567890)
        self.assertEqual(config.telegram_bot_token, "invalid")
        self.assertEqual(config.telegram_api_base_url, "https://api.telegram.org")
        self.assertEqual(config.telegram_auth_key, "it_is_really_telegram")
        self.assertEqual(config.telegram_must_auth, False)
        self.assertEqual(config.chat_history_depth, 30)
        self.assertEqual(config.anthropic_token, "invalid")
        self.assertEqual(config.open_ai_token, "invalid")
        self.assertEqual(config.rapid_api_token, "invalid")
        self.assertEqual(config.rapid_api_twitter_token, "invalid")
        self.assertEqual(config.coinmarketcap_api_token, "invalid")
        self.assertEqual(config.replicate_api_token, "invalid")
        self.assertEqual(config.perplexity_api_token, "invalid")
        self.assertEqual(config.github_issues_token, "invalid")
        self.assertEqual(config.github_issues_repo, "appifyhub/the-agent")
        self.assertEqual(config.issue_templates_abs_path, ".github/ISSUE_TEMPLATE")
        self.assertEqual(config.jwt_secret_key, "default")
        self.assertEqual(config.jwt_expires_in_minutes, 5)
        self.assertEqual(config.backoffice_url_base, "https://web.agent.appifyhub.com")
        self.assertEqual(config.version, "dev")

    def test_custom_config(self):
        os.environ["VERBOSE"] = "true"
        os.environ["LOG_TG_UPDATE"] = "true"
        os.environ["WEB_RETRIES"] = "5"
        os.environ["WEB_RETRY_DELAY_S"] = "2"
        os.environ["WEB_TIMEOUT_S"] = "20"
        os.environ["MAX_INVITES_PER_USER"] = "5"
        os.environ["MAX_USERS"] = "10"
        os.environ["WEBSITE_URL"] = "https://new.agent.appifyhub.com"
        os.environ["POSTGRES_USER"] = "admin"
        os.environ["POSTGRES_PASS"] = "admin123"
        os.environ["POSTGRES_HOST"] = "db.example.com"
        os.environ["POSTGRES_DB"] = "test_db"
        os.environ["API_KEY"] = "1111-2222-3333-4444"
        os.environ["PARENT_ORGANIZATION"] = "New"
        os.environ["TELEGRAM_BOT_USERNAME"] = "the_new_agent"
        os.environ["TELEGRAM_BOT_NAME"] = "The New Agent"
        os.environ["TELEGRAM_BOT_ID"] = "1234"
        os.environ["TELEGRAM_BOT_TOKEN"] = "id:sha"
        os.environ["TELEGRAM_API_BASE_URL"] = "https://new.api.telegram.org"
        os.environ["TELEGRAM_API_UPDATE_AUTH_TOKEN"] = "abcd1234"
        os.environ["TELEGRAM_AUTH_ON"] = "true"
        os.environ["CHAT_HISTORY_DEPTH"] = "10"
        os.environ["ANTHROPIC_TOKEN"] = "sk-a-valid"
        os.environ["OPEN_AI_TOKEN"] = "sk-o-valid"
        os.environ["RAPID_API_TOKEN"] = "sk-r-valid"
        os.environ["RAPID_API_TWITTER_TOKEN"] = "sk-rt-valid"
        os.environ["COINMARKETCAP_API_TOKEN"] = "sk-c-valid"
        os.environ["REPLICATE_API_TOKEN"] = "sk-re-valid"
        os.environ["PERPLEXITY_API_TOKEN"] = "sk-p-valid"
        os.environ["THE_AGENT_ISSUES_TOKEN"] = "sk-gi-valid"
        os.environ["THE_AGENT_ISSUES_REPO"] = "appifyhub/the-new-agent"
        os.environ["THE_AGENT_ISSUE_TEMPLATES_PATH"] = "issue_templates"
        os.environ["JWT_SECRET_KEY"] = "custom"
        os.environ["JWT_EXPIRES_IN_MINUTES"] = "10"
        os.environ["BACKOFFICE_URL_BASE"] = "https://example.com"
        os.environ["VERSION"] = "custom"

        config = Config()

        self.assertEqual(config.verbose, True)
        self.assertEqual(config.log_telegram_update, True)
        self.assertEqual(config.web_retries, 5)
        self.assertEqual(config.web_retry_delay_s, 2)
        self.assertEqual(config.web_timeout_s, 20)
        self.assertEqual(config.max_invites_per_user, 5)
        self.assertEqual(config.max_users, 10)
        self.assertEqual(config.website_url, "https://new.agent.appifyhub.com")
        self.assertEqual(config.db_url, "postgresql://admin:admin123@db.example.com:5432/test_db")
        self.assertEqual(config.api_key, "1111-2222-3333-4444")
        self.assertEqual(config.parent_organization, "New")
        self.assertEqual(config.telegram_bot_username, "the_new_agent")
        self.assertEqual(config.telegram_bot_name, "The New Agent")
        self.assertEqual(config.telegram_bot_id, 1234)
        self.assertEqual(config.telegram_bot_token, "id:sha")
        self.assertEqual(config.telegram_api_base_url, "https://new.api.telegram.org")
        self.assertEqual(config.telegram_auth_key, "abcd1234")
        self.assertEqual(config.telegram_must_auth, True)
        self.assertEqual(config.chat_history_depth, 10)
        self.assertEqual(config.anthropic_token, "sk-a-valid")
        self.assertEqual(config.open_ai_token, "sk-o-valid")
        self.assertEqual(config.rapid_api_token, "sk-r-valid")
        self.assertEqual(config.rapid_api_twitter_token, "sk-rt-valid")
        self.assertEqual(config.coinmarketcap_api_token, "sk-c-valid")
        self.assertEqual(config.replicate_api_token, "sk-re-valid")
        self.assertEqual(config.perplexity_api_token, "sk-p-valid")
        self.assertEqual(config.github_issues_token, "sk-gi-valid")
        self.assertEqual(config.github_issues_repo, "appifyhub/the-new-agent")
        self.assertEqual(config.issue_templates_abs_path, "issue_templates")
        self.assertEqual(config.jwt_secret_key, "custom")
        self.assertEqual(config.jwt_expires_in_minutes, 10)
        self.assertEqual(config.backoffice_url_base, "https://example.com")
        self.assertEqual(config.version, "custom")
