# ruff: noqa: E501

import os
from typing import Callable

from pydantic import SecretStr

from util.singleton import Singleton


class Config(metaclass = Singleton):

    DEV_API_KEY = "0000-1234-5678-0000"  # needed for local dev mode

    max_sponsorships_per_user: int
    log_level: str
    log_telegram_update: bool
    log_whatsapp_update: bool
    web_retries: int
    web_retry_delay_s: int
    web_timeout_s: int
    max_users: int
    max_chatbot_iterations: int
    website_url: str
    parent_organization: str
    agent_bot_name: str
    background_bot_name: str
    background_bot_username: str
    github_bot_username: str
    github_bot_id: int
    telegram_bot_username: str
    telegram_bot_id: int
    telegram_api_base_url: str
    telegram_must_auth: bool
    whatsapp_must_auth: bool
    whatsapp_phone_number_id: str
    whatsapp_bot_phone_number: str
    chat_history_depth: int
    github_issues_repo: str
    issue_templates_abs_path: str
    jwt_expires_in_minutes: int
    backoffice_url_base: str
    main_language_name: str = "English"
    main_language_iso_code: str = "en"
    uploadcare_public_key: str
    uploadcare_cdn_id: str
    version: str

    db_url: SecretStr
    api_key: SecretStr
    telegram_auth_key: SecretStr
    telegram_bot_token: SecretStr
    whatsapp_auth_key: SecretStr
    whatsapp_app_secret: SecretStr
    whatsapp_bot_token: SecretStr
    jwt_secret_key: SecretStr
    github_issues_token: SecretStr
    rapid_api_twitter_token: SecretStr
    free_img_host_token: SecretStr
    token_encrypt_secret: SecretStr
    uploadcare_private_key: SecretStr

    def all_secrets(self) -> list[SecretStr]:
        return [
            self.db_url,
            self.api_key,
            self.telegram_auth_key,
            self.telegram_bot_token,
            self.whatsapp_auth_key,
            self.whatsapp_app_secret,
            self.whatsapp_bot_token,
            self.jwt_secret_key,
            self.github_issues_token,
            self.rapid_api_twitter_token,
            self.free_img_host_token,
            self.token_encrypt_secret,
            self.uploadcare_private_key,
        ]

    def __init__(
        self,
        def_max_sponsorships_per_user: int = 2,
        def_log_level: str = "INFO",
        def_log_telegram_update: bool = False,
        def_log_whatsapp_update: bool = False,
        def_web_retries: int = 3,
        def_web_retry_delay_s: int = 1,
        def_web_timeout_s: int = 10,
        def_max_users: int = 100,
        def_max_chatbot_iterations: int = 20,
        def_website_url: str = "https://agent.appifyhub.com",
        def_parent_organization: str = "AppifyHub",
        def_agent_bot_name: str = "The Agent",
        def_background_bot_name: str = "The Agent's Pulse",
        def_background_bot_username: str = "the_agent_pulse",
        def_github_bot_username: str = "the-agent",
        def_github_bot_id: int = 1234567890,
        def_telegram_bot_username: str = "the_agent",
        def_telegram_bot_id: int = 1234567890,
        def_telegram_api_base_url: str = "https://api.telegram.org",
        def_telegram_must_auth: bool = False,
        def_whatsapp_must_auth: bool = False,
        def_whatsapp_phone_number_id: str = "invalid",
        def_whatsapp_bot_phone_number: str = "11234567890",
        def_chat_history_depth: int = 30,
        def_github_issues_repo: str = "appifyhub/the-agent",
        def_issue_templates_path: str = ".github/ISSUE_TEMPLATE",
        def_jwt_expires_in_minutes: int = 5,
        def_backoffice_url_base: str = "http://127.0.0.1.sslip.io:5173",
        def_main_language_name: str = "English",
        def_main_language_iso_code: str = "en",
        def_uploadcare_public_key: str = "invalid",
        def_uploadcare_cdn_id: str = "invalid",
        def_version: str = "dev",

        def_db_user: SecretStr = SecretStr("root"),
        def_db_pass: SecretStr = SecretStr("root"),
        def_db_host: SecretStr = SecretStr("localhost"),
        def_db_name: SecretStr = SecretStr("agent"),
        def_api_key: SecretStr = SecretStr(DEV_API_KEY),
        def_telegram_auth_key: SecretStr = SecretStr("it_is_really_telegram"),
        def_telegram_bot_token: SecretStr = SecretStr("invalid"),
        def_whatsapp_auth_key: SecretStr = SecretStr("it_is_really_whatsapp"),
        def_whatsapp_app_secret: SecretStr = SecretStr("invalid"),
        def_whatsapp_bot_token: SecretStr = SecretStr("invalid"),
        def_jwt_secret_key: SecretStr = SecretStr("default"),
        def_github_issues_token: SecretStr = SecretStr("invalid"),
        def_rapid_api_twitter_token: SecretStr = SecretStr("invalid"),
        def_free_img_host_token: SecretStr = SecretStr("invalid"),
        def_token_encrypt_secret: SecretStr = SecretStr("default"),
        def_uploadcare_private_key: SecretStr = SecretStr("invalid"),
    ):
        # @formatter:off
        self.max_sponsorships_per_user = int(self.__env("MAX_SPONSORSHIPS_PER_USER", lambda: str(def_max_sponsorships_per_user)))
        self.log_level = self.__env("LOG_LEVEL", lambda: def_log_level).lower()
        self.log_telegram_update = self.__env("LOG_TG_UPDATE", lambda: str(def_log_telegram_update)).lower() == "true"
        self.log_whatsapp_update = self.__env("LOG_WA_UPDATE", lambda: str(def_log_whatsapp_update)).lower() == "true"
        self.web_retries = int(self.__env("WEB_RETRIES", lambda: str(def_web_retries)))
        self.web_retry_delay_s = int(self.__env("WEB_RETRY_DELAY_S", lambda: str(def_web_retry_delay_s)))
        self.web_timeout_s = int(self.__env("WEB_TIMEOUT_S", lambda: str(def_web_timeout_s)))
        self.max_users = int(self.__env("MAX_USERS", lambda: str(def_max_users)))
        self.max_chatbot_iterations = int(self.__env("MAX_CHATBOT_ITERATIONS", lambda: str(def_max_chatbot_iterations)))
        self.website_url = self.__env("WEBSITE_URL", lambda: def_website_url)
        self.parent_organization = self.__env("PARENT_ORGANIZATION", lambda: def_parent_organization)
        self.agent_bot_name = self.__env("AGENT_BOT_NAME", lambda: def_agent_bot_name)
        self.background_bot_name = self.__env("BACKGROUND_BOT_NAME", lambda: def_background_bot_name)
        self.background_bot_username = self.__env("BACKGROUND_BOT_USERNAME", lambda: def_background_bot_username)
        self.github_bot_username = self.__env("GITHUB_BOT_USERNAME", lambda: def_github_bot_username)
        self.github_bot_id = int(self.__env("GITHUB_BOT_ID", lambda: str(def_github_bot_id)))
        self.telegram_bot_username = self.__env("TELEGRAM_BOT_USERNAME", lambda: def_telegram_bot_username)
        self.telegram_bot_id = int(self.__env("TELEGRAM_BOT_ID", lambda: str(def_telegram_bot_id)))
        self.telegram_api_base_url = self.__env("TELEGRAM_API_BASE_URL", lambda: def_telegram_api_base_url)
        self.telegram_must_auth = self.__env("TELEGRAM_AUTH_ON", lambda: str(def_telegram_must_auth)).lower() == "true"
        self.whatsapp_must_auth = self.__env("WHATSAPP_AUTH_ON", lambda: str(def_whatsapp_must_auth)).lower() == "true"
        self.whatsapp_phone_number_id = self.__env("WHATSAPP_PHONE_NUMBER_ID", lambda: def_whatsapp_phone_number_id)
        self.whatsapp_bot_phone_number = self.__env("WHATSAPP_BOT_PHONE_NUMBER", lambda: def_whatsapp_bot_phone_number)
        self.chat_history_depth = int(self.__env("CHAT_HISTORY_DEPTH", lambda: str(def_chat_history_depth)))
        self.github_issues_repo = self.__env("THE_AGENT_ISSUES_REPO", lambda: def_github_issues_repo)
        self.issue_templates_abs_path = self.__env("THE_AGENT_ISSUE_TEMPLATES_PATH", lambda: def_issue_templates_path)
        self.jwt_expires_in_minutes = int(self.__env("JWT_EXPIRES_IN_MINUTES", lambda: str(def_jwt_expires_in_minutes)))
        self.backoffice_url_base = self.__env("BACKOFFICE_URL_BASE", lambda: def_backoffice_url_base)
        self.main_language_name = self.__env("MAIN_LANGUAGE_NAME", lambda: def_main_language_name)
        self.main_language_iso_code = self.__env("MAIN_LANGUAGE_ISO_CODE", lambda: def_main_language_iso_code)
        self.uploadcare_public_key = self.__env("UPLOADCARE_PUBLIC_KEY", lambda: def_uploadcare_public_key)
        self.uploadcare_cdn_id = self.__env("UPLOADCARE_CDN_ID", lambda: def_uploadcare_cdn_id)
        self.version = self.__env("VERSION", lambda: def_version)

        self.__set_up_db(def_db_user, def_db_pass, def_db_host, def_db_name)
        self.api_key = self.__senv("API_KEY", lambda: def_api_key)
        self.telegram_auth_key = self.__senv("TELEGRAM_API_UPDATE_AUTH_TOKEN", lambda: def_telegram_auth_key)
        self.telegram_bot_token = self.__senv("TELEGRAM_BOT_TOKEN", lambda: def_telegram_bot_token)
        self.whatsapp_auth_key = self.__senv("WHATSAPP_API_UPDATE_AUTH_TOKEN", lambda: def_whatsapp_auth_key)
        self.whatsapp_app_secret = self.__senv("WHATSAPP_APP_SECRET", lambda: def_whatsapp_app_secret)
        self.whatsapp_bot_token = self.__senv("WHATSAPP_BOT_TOKEN", lambda: def_whatsapp_bot_token)
        self.jwt_secret_key = self.__senv("JWT_SECRET_KEY", lambda: def_jwt_secret_key)
        self.github_issues_token = self.__senv("THE_AGENT_ISSUES_TOKEN", lambda: def_github_issues_token)
        self.rapid_api_twitter_token = self.__senv("RAPID_API_TWITTER_TOKEN", lambda: def_rapid_api_twitter_token)
        self.free_img_host_token = self.__senv("FREE_IMG_HOST_TOKEN", lambda: def_free_img_host_token)
        self.token_encrypt_secret = self.__senv("TOKEN_ENCRYPT_SECRET", lambda: def_token_encrypt_secret)
        self.uploadcare_private_key = self.__senv("UPLOADCARE_PRIVATE_KEY", lambda: def_uploadcare_private_key)
        # @formatter:on

    def __set_up_db(self, def_db_user: SecretStr, def_db_pass: SecretStr, def_db_host: SecretStr, def_db_name: SecretStr):
        db_user = self.__senv("POSTGRES_USER", lambda: def_db_user).get_secret_value()
        db_pass = self.__senv("POSTGRES_PASS", lambda: def_db_pass).get_secret_value()
        db_host = self.__senv("POSTGRES_HOST", lambda: def_db_host).get_secret_value()
        db_name = self.__senv("POSTGRES_DB", lambda: def_db_name).get_secret_value()
        db_port = 5432  # standard for postgres
        self.db_url = SecretStr(f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}")

    @staticmethod
    def __env(name: str, default: Callable[[], str]) -> str:
        env_value = os.environ.get(name, "").strip()
        return env_value if env_value else default()

    @staticmethod
    def __senv(name: str, default: Callable[[], SecretStr]) -> SecretStr:
        env_value = os.environ.get(name, "").strip()
        return SecretStr(env_value) if env_value else default()


config = Config()
