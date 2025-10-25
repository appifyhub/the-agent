import os
import unittest

from util.config import Config


class ConfigTest(unittest.TestCase):

    # noinspection PyTypeHints
    original_env: dict

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

        self.assertEqual(config.log_level, "info")
        self.assertEqual(config.log_telegram_update, False)
        self.assertEqual(config.web_retries, 3)
        self.assertEqual(config.web_retry_delay_s, 1)
        self.assertEqual(config.web_timeout_s, 10)
        self.assertEqual(config.max_sponsorships_per_user, 2)
        self.assertEqual(config.max_users, 100)
        self.assertEqual(config.max_chatbot_iterations, 20)
        self.assertEqual(config.website_url, "https://agent.appifyhub.com")
        self.assertEqual(config.parent_organization, "AppifyHub")
        self.assertEqual(config.background_bot_name, "The Agent's Pulse")
        self.assertEqual(config.background_bot_username, "the_agent_pulse")
        self.assertEqual(config.github_bot_username, "the-agent")
        self.assertEqual(config.github_bot_name, "The Agent")
        self.assertEqual(config.github_bot_id, 1234567890)
        self.assertEqual(config.telegram_bot_username, "the_agent")
        self.assertEqual(config.telegram_bot_name, "The Agent")
        self.assertEqual(config.telegram_bot_id, 1234567890)
        self.assertEqual(config.telegram_api_base_url, "https://api.telegram.org")
        self.assertEqual(config.telegram_must_auth, False)
        self.assertEqual(config.whatsapp_must_auth, False)
        self.assertEqual(config.whatsapp_phone_number_id, "invalid")
        self.assertEqual(config.whatsapp_bot_phone_number, "11234567890")
        self.assertEqual(config.whatsapp_bot_name, "The Agent")
        self.assertEqual(config.chat_history_depth, 30)
        self.assertEqual(config.github_issues_repo, "appifyhub/the-agent")
        self.assertEqual(config.issue_templates_abs_path, ".github/ISSUE_TEMPLATE")
        self.assertEqual(config.jwt_expires_in_minutes, 5)
        self.assertEqual(config.backoffice_url_base, "http://127.0.0.1.sslip.io:5173")
        self.assertEqual(config.main_language_name, "English")
        self.assertEqual(config.main_language_iso_code, "en")
        self.assertEqual(config.uploadcare_public_key, "invalid")
        self.assertEqual(config.uploadcare_cdn_id, "invalid")
        self.assertEqual(config.version, "dev")

        self.assertEqual(config.db_url.get_secret_value(), "postgresql://root:root@localhost:5432/agent")
        self.assertTrue(config.api_key.get_secret_value())  # Check if API key is generated
        self.assertEqual(config.telegram_auth_key.get_secret_value(), "it_is_really_telegram")
        self.assertEqual(config.telegram_bot_token.get_secret_value(), "invalid")
        self.assertEqual(config.whatsapp_auth_key.get_secret_value(), "it_is_really_whatsapp")
        self.assertEqual(config.whatsapp_app_secret.get_secret_value(), "invalid")
        self.assertEqual(config.jwt_secret_key.get_secret_value(), "default")
        self.assertEqual(config.github_issues_token.get_secret_value(), "invalid")
        self.assertEqual(config.rapid_api_twitter_token.get_secret_value(), "invalid")
        self.assertEqual(config.free_img_host_token.get_secret_value(), "invalid")
        self.assertEqual(config.token_encrypt_secret.get_secret_value(), "default")
        self.assertEqual(config.uploadcare_private_key.get_secret_value(), "invalid")

    def test_custom_config(self):
        os.environ["LOG_LEVEL"] = "DEBUG"
        os.environ["LOG_TG_UPDATE"] = "true"
        os.environ["WEB_RETRIES"] = "5"
        os.environ["WEB_RETRY_DELAY_S"] = "2"
        os.environ["WEB_TIMEOUT_S"] = "20"
        os.environ["MAX_SPONSORSHIPS_PER_USER"] = "5"
        os.environ["MAX_USERS"] = "10"
        os.environ["MAX_CHATBOT_ITERATIONS"] = "15"
        os.environ["WEBSITE_URL"] = "https://new.agent.appifyhub.com"
        os.environ["PARENT_ORGANIZATION"] = "New"
        os.environ["BACKGROUND_BOT_NAME"] = "The New Agent's Pulse"
        os.environ["BACKGROUND_BOT_USERNAME"] = "the_new_agent_pulse"
        os.environ["GITHUB_BOT_USERNAME"] = "the-new-agent"
        os.environ["GITHUB_BOT_NAME"] = "The New Agent"
        os.environ["GITHUB_BOT_ID"] = "1234"
        os.environ["TELEGRAM_BOT_USERNAME"] = "the_new_agent"
        os.environ["TELEGRAM_BOT_NAME"] = "The New Agent"
        os.environ["TELEGRAM_BOT_ID"] = "1234"
        os.environ["TELEGRAM_API_BASE_URL"] = "https://new.api.telegram.org"
        os.environ["TELEGRAM_AUTH_ON"] = "True"
        os.environ["WHATSAPP_AUTH_ON"] = "True"
        os.environ["WHATSAPP_PHONE_NUMBER_ID"] = "9876543210"
        os.environ["WHATSAPP_BOT_PHONE_NUMBER"] = "19876543210"
        os.environ["WHATSAPP_BOT_NAME"] = "The New Agent"
        os.environ["CHAT_HISTORY_DEPTH"] = "10"
        os.environ["THE_AGENT_ISSUES_REPO"] = "appifyhub/the-new-agent"
        os.environ["THE_AGENT_ISSUE_TEMPLATES_PATH"] = "issue_templates"
        os.environ["JWT_EXPIRES_IN_MINUTES"] = "10"
        os.environ["BACKOFFICE_URL_BASE"] = "https://example.com"
        os.environ["MAIN_LANGUAGE_NAME"] = "German"
        os.environ["MAIN_LANGUAGE_ISO_CODE"] = "de"
        os.environ["UPLOADCARE_PUBLIC_KEY"] = "public-key-123"
        os.environ["UPLOADCARE_CDN_ID"] = "cdn-id-123"
        os.environ["VERSION"] = "custom"

        os.environ["POSTGRES_USER"] = "admin"
        os.environ["POSTGRES_PASS"] = "admin123"
        os.environ["POSTGRES_HOST"] = "db.example.com"
        os.environ["POSTGRES_DB"] = "test_db"
        os.environ["API_KEY"] = "1111-2222-3333-4444"
        os.environ["TELEGRAM_API_UPDATE_AUTH_TOKEN"] = "abcd1234"
        os.environ["TELEGRAM_BOT_TOKEN"] = "id:sha"
        os.environ["WHATSAPP_API_UPDATE_AUTH_TOKEN"] = "efgh5678"
        os.environ["WHATSAPP_APP_SECRET"] = "ijkl9012"
        os.environ["WHATSAPP_BOT_TOKEN"] = "bot_token_123"
        os.environ["JWT_SECRET_KEY"] = "custom"
        os.environ["THE_AGENT_ISSUES_TOKEN"] = "sk-gi-valid"
        os.environ["RAPID_API_TWITTER_TOKEN"] = "sk-rt-valid"
        os.environ["FREE_IMG_HOST_TOKEN"] = "sk-im-valid"
        os.environ["TOKEN_ENCRYPT_SECRET"] = "custom-encryption-key"
        os.environ["UPLOADCARE_PRIVATE_KEY"] = "private-key-123"

        config = Config()

        self.assertEqual(config.log_level, "debug")
        self.assertEqual(config.log_telegram_update, True)
        self.assertEqual(config.web_retries, 5)
        self.assertEqual(config.web_retry_delay_s, 2)
        self.assertEqual(config.web_timeout_s, 20)
        self.assertEqual(config.max_sponsorships_per_user, 5)
        self.assertEqual(config.max_users, 10)
        self.assertEqual(config.max_chatbot_iterations, 15)
        self.assertEqual(config.website_url, "https://new.agent.appifyhub.com")
        self.assertEqual(config.parent_organization, "New")
        self.assertEqual(config.background_bot_name, "The New Agent's Pulse")
        self.assertEqual(config.background_bot_username, "the_new_agent_pulse")
        self.assertEqual(config.github_bot_username, "the-new-agent")
        self.assertEqual(config.github_bot_name, "The New Agent")
        self.assertEqual(config.github_bot_id, 1234)
        self.assertEqual(config.telegram_bot_username, "the_new_agent")
        self.assertEqual(config.telegram_bot_name, "The New Agent")
        self.assertEqual(config.telegram_bot_id, 1234)
        self.assertEqual(config.telegram_api_base_url, "https://new.api.telegram.org")
        self.assertEqual(config.telegram_must_auth, True)
        self.assertEqual(config.whatsapp_must_auth, True)
        self.assertEqual(config.whatsapp_phone_number_id, "9876543210")
        self.assertEqual(config.whatsapp_bot_phone_number, "19876543210")
        self.assertEqual(config.whatsapp_bot_name, "The New Agent")
        self.assertEqual(config.chat_history_depth, 10)
        self.assertEqual(config.github_issues_repo, "appifyhub/the-new-agent")
        self.assertEqual(config.issue_templates_abs_path, "issue_templates")
        self.assertEqual(config.jwt_expires_in_minutes, 10)
        self.assertEqual(config.backoffice_url_base, "https://example.com")
        self.assertEqual(config.main_language_name, "German")
        self.assertEqual(config.main_language_iso_code, "de")
        self.assertEqual(config.uploadcare_public_key, "public-key-123")
        self.assertEqual(config.uploadcare_cdn_id, "cdn-id-123")
        self.assertEqual(config.version, "custom")

        self.assertEqual(config.db_url.get_secret_value(), "postgresql://admin:admin123@db.example.com:5432/test_db")
        self.assertEqual(config.api_key.get_secret_value(), "1111-2222-3333-4444")
        self.assertEqual(config.telegram_auth_key.get_secret_value(), "abcd1234")
        self.assertEqual(config.telegram_bot_token.get_secret_value(), "id:sha")
        self.assertEqual(config.whatsapp_auth_key.get_secret_value(), "efgh5678")
        self.assertEqual(config.whatsapp_app_secret.get_secret_value(), "ijkl9012")
        self.assertEqual(config.whatsapp_bot_token.get_secret_value(), "bot_token_123")
        self.assertEqual(config.jwt_secret_key.get_secret_value(), "custom")
        self.assertEqual(config.github_issues_token.get_secret_value(), "sk-gi-valid")
        self.assertEqual(config.rapid_api_twitter_token.get_secret_value(), "sk-rt-valid")
        self.assertEqual(config.free_img_host_token.get_secret_value(), "sk-im-valid")
        self.assertEqual(config.token_encrypt_secret.get_secret_value(), "custom-encryption-key")
        self.assertEqual(config.uploadcare_private_key.get_secret_value(), "private-key-123")
