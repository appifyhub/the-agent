import os
from typing import Callable

from util.singleton import Singleton


class Config(metaclass = Singleton):
    verbose: bool
    web_retries: int
    web_retry_delay_s: int
    web_timeout_s: int
    max_invites_per_user: int
    max_users: int
    website_url: str
    db_url: str
    api_key: str
    parent_organization: str
    telegram_bot_username: str
    telegram_bot_name: str
    telegram_bot_token: str
    telegram_api_base_url: str
    chat_history_depth: int
    anthropic_token: str
    open_ai_token: str
    rapid_api_token: str
    coin_api_token: str

    def __init__(
        self,
        def_verbose: bool = False,
        def_web_retries: int = 3,
        def_web_retry_delay_s: int = 1,
        def_web_timeout_s: int = 10,
        def_max_invites_per_user: int = 2,
        def_max_users: int = 100,
        def_website_url: str = "https://the-agent.appifyhub.com",
        def_db_user: str = "root",
        def_db_pass: str = "root",
        def_db_host: str = "localhost",
        def_db_name: str = "agent",
        def_api_key: str = "0000-1234-5678-0000",
        def_parent_organization: str = "AppifyHub",
        def_telegram_bot_username: str = "the_agent",
        def_telegram_bot_name: str = "The Agent",
        def_telegram_bot_token: str = "invalid",
        def_telegram_api_base_url: str = "https://api.telegram.org",
        def_chat_history_depth: int = 30,
        def_anthropic_token: str = "invalid",
        def_open_ai_token: str = "invalid",
        def_rapid_api_token: str = "invalid",
        def_coin_api_token: str = "invalid",
    ):
        self.verbose = self.__env("VERBOSE", lambda: str(def_verbose)).lower() == "true"
        self.web_retries = int(self.__env("WEB_RETRIES", lambda: str(def_web_retries)))
        self.web_retry_delay_s = int(self.__env("WEB_RETRY_DELAY_S", lambda: str(def_web_retry_delay_s)))
        self.web_timeout_s = int(self.__env("WEB_TIMEOUT_S", lambda: str(def_web_timeout_s)))
        self.max_invites_per_user = int(self.__env("MAX_INVITES_PER_USER", lambda: str(def_max_invites_per_user)))
        self.max_users = int(self.__env("MAX_USERS", lambda: str(def_max_users)))
        self.website_url = self.__env("WEBSITE_URL", lambda: def_website_url)
        self.__set_up_db(def_db_user, def_db_pass, def_db_host, def_db_name)
        self.api_key = self.__env("API_KEY", lambda: def_api_key)
        self.parent_organization = self.__env("PARENT_ORGANIZATION", lambda: def_parent_organization)
        self.telegram_bot_username = self.__env("TELEGRAM_BOT_USERNAME", lambda: def_telegram_bot_username)
        self.telegram_bot_name = self.__env("TELEGRAM_BOT_NAME", lambda: def_telegram_bot_name)
        self.telegram_bot_token = self.__env("TELEGRAM_BOT_TOKEN", lambda: def_telegram_bot_token)
        self.telegram_api_base_url = self.__env("TELEGRAM_API_BASE_URL", lambda: def_telegram_api_base_url)
        self.chat_history_depth = int(self.__env("CHAT_HISTORY_DEPTH", lambda: str(def_chat_history_depth)))
        self.anthropic_token = self.__env("ANTHROPIC_TOKEN", lambda: def_anthropic_token)
        self.open_ai_token = self.__env("OPEN_AI_TOKEN", lambda: def_open_ai_token)
        self.rapid_api_token = self.__env("RAPID_API_TOKEN", lambda: def_rapid_api_token)
        self.coin_api_token = self.__env("COIN_API_TOKEN", lambda: def_coin_api_token)

    def __set_up_db(self, def_db_user: str, def_db_pass: str, def_db_host: str, def_db_name: str) -> None:
        db_user = self.__env("POSTGRES_USER", lambda: def_db_user)
        db_pass = self.__env("POSTGRES_PASS", lambda: def_db_pass)
        db_host = self.__env("POSTGRES_HOST", lambda: def_db_host)
        db_name = self.__env("POSTGRES_DB", lambda: def_db_name)
        db_port = 5432  # standard for postgres
        self.db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    @staticmethod
    def __env(name: str, default: Callable[[], str]) -> str:
        env_value = os.environ.get(name, "").strip()
        return env_value if env_value else default()


config = Config()
