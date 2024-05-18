import os
import random
import string
from typing import Callable

from util.safe_printer_mixin import SafePrinterMixin
from util.singleton import Singleton


class Config(SafePrinterMixin, metaclass = Singleton):
    verbose: bool
    web_retries: int
    web_retry_delay_s: int
    web_timeout_s: int
    max_invites_per_user: int
    db_url: str
    api_key: str

    def __init__(
        self,
        def_verbose: bool = False,
        def_web_retries: int = 3,
        def_web_retry_delay_s: int = 1,
        def_web_timeout_s: int = 10,
        def_max_invites_per_user: int = 2,
        def_db_user: str = "root",
        def_db_pass: str = "root",
        def_db_host: str = "localhost",
        def_db_name: str = "agent",
    ):
        self.verbose = self.__env("VERBOSE", lambda: str(def_verbose)).lower() == "true"
        super().__init__(self.verbose)
        self.web_retries = int(self.__env("WEB_RETRIES", lambda: str(def_web_retries)))
        self.web_retry_delay_s = int(self.__env("WEB_RETRY_DELAY_S", lambda: str(def_web_retry_delay_s)))
        self.web_timeout_s = int(self.__env("WEB_TIMEOUT_S", lambda: str(def_web_timeout_s)))
        self.max_invites_per_user = int(self.__env("MAX_INVITES_PER_USER", lambda: str(def_max_invites_per_user)))
        self.api_key = self.__env("API_KEY", self.__generate_api_key)
        self.__set_up_db(def_db_user, def_db_pass, def_db_host, def_db_name)

    def __generate_api_key(self) -> str:
        self.sprint("\nGenerating a random API key...")
        api_key = Config.__random_key()
        api_key_message = f"API Key: '{api_key}'"
        border = '*' * len(api_key_message)
        self.sprint("Done!\n")
        self.sprint(border)
        self.sprint(api_key_message)
        self.sprint(f"{border}\n")
        return api_key

    def __set_up_db(
        self,
        def_db_user: str,
        def_db_pass: str,
        def_db_host: str,
        def_db_name: str,
    ) -> None:
        db_user = self.__env("POSTGRES_USER", lambda: def_db_user)
        db_pass = self.__env("POSTGRES_PASS", lambda: def_db_pass)
        db_host = self.__env("POSTGRES_HOST", lambda: def_db_host)
        db_name = self.__env("POSTGRES_DB", lambda: def_db_name)
        db_port = 5432  # standard for postgres
        self.db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        self.sprint(f"Database configured!\nURL: '{self.db_url}'\n")

    @staticmethod
    def __env(name: str, default: Callable[[], str]) -> str:
        raw_env = os.environ.get(name, "").strip()
        return raw_env if raw_env else default()

    @staticmethod
    def __random_key(length: int = 16) -> str:
        letters_and_digits = string.ascii_letters + string.digits
        content = ''.join(random.choice(letters_and_digits) for _ in range(length))
        formatted = '-'.join(content[i:i + 4] for i in range(0, len(content), 4))
        return formatted.upper()


instance = Config()
