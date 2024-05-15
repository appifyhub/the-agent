import platform
import time
from typing import Optional

import requests
from requests.exceptions import RequestException, Timeout

from config import Config
from safe_printer_mixin import SafePrinterMixin


PLATFORM = f"{platform.python_implementation()}/{platform.python_version()}"
USER_AGENT = f"Mozilla/5.0 (compatible; TheAgent/1.0; {PLATFORM})"
HEADERS = { "User-Agent": USER_AGENT }

class WebFetcher(SafePrinterMixin):
    url: str
    html: Optional[str] = None
    json: Optional[dict] = None
    __config: Config

    def __init__(
        self,
        url: str,
        config: Config,
        auto_fetch_html: bool = False,
        auto_fetch_json: bool = False,
    ):
        super().__init__(config.verbose)
        self.url = url
        self.__config = config
        if auto_fetch_html:
            self.fetch_html()
        if auto_fetch_json:
            self.fetch_json()

    def fetch_html(self) -> Optional[str]:
        self.html = None  # reset value
        attempts = 0
        for _ in range(self.__config.web_retries):
            try:
                response = requests.get(self.url, headers = HEADERS, timeout = self.__config.web_timeout_s)
                response.raise_for_status()
                self.html = response.text
            except (RequestException, Timeout) as e:
                attempts += 1
                attempts_left = self.__config.web_retries - attempts + 1
                self.sprint(f"Error fetching HTML content: {e}. Retries left: {attempts_left}.")
                time.sleep(self.__config.web_retry_delay_s)
        return self.html

    def fetch_json(self) -> Optional[dict]:
        self.json = None
        attempts = 0
        for _ in range(self.__config.web_retries):
            try:
                response = requests.get(self.url, headers = HEADERS, timeout = self.__config.web_timeout_s)
                response.raise_for_status()
                self.json = response.json()
            except (RequestException, Timeout) as e:
                attempts += 1
                attempts_left = self.__config.web_retries - attempts + 1
                self.sprint(f"Error fetching JSON content: {e}. Retries left: {attempts_left}.")
                time.sleep(self.__config.web_retry_delay_s)
        return self.json
