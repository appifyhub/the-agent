import os
import random
import string
from typing import Callable

from safe_printer_mixin import SafePrinterMixin


class Config(SafePrinterMixin):
    verbose: bool
    web_retries: int
    web_retry_delay_s: int
    web_timeout_s: int
    api_key: str

    def __init__(
        self,
        def_verbose: bool = False,
        def_web_retries: int = 3,
        def_web_retry_delay_s: int = 1,
        def_web_timeout_s: int = 10,
    ):
        self.verbose = self.__env("VERBOSE", lambda: str(def_verbose)).lower() == "true"
        super().__init__(self.verbose)
        self.web_retries = int(self.__env("WEB_RETRIES", lambda: str(def_web_retries)))
        self.web_retry_delay_s = int(self.__env("WEB_RETRY_DELAY_S", lambda: str(def_web_retry_delay_s)))
        self.web_timeout_s = int(self.__env("WEB_TIMEOUT_S", lambda: str(def_web_timeout_s)))
        self.api_key = self.__env("API_KEY", self.__generate_api_key)

    def __generate_api_key(self) -> str:
        self.sprint("Generating a random API key...")
        api_key = Config.__random_key()
        api_key_message = f"API Key: '{api_key}'"
        border = '*' * len(api_key_message)
        self.sprint("Done!\n")
        self.sprint(border)
        self.sprint(api_key_message)
        self.sprint(f"{border}\n")
        return api_key

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
