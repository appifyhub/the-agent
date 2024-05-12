import platform
import time
from typing import Optional

import requests
from requests.exceptions import RequestException, Timeout

from safe_printer_mixin import SafePrinterMixin


PLATFORM = f"{platform.python_implementation()}/{platform.python_version()}"
USER_AGENT = f"Mozilla/5.0 (compatible; TheAgent/1.0; {PLATFORM})"
HEADERS = { "User-Agent": USER_AGENT }
DEFAULT_SLEEP_S = 2

class WebFetcher(SafePrinterMixin):
    url: str
    html: Optional[str] = None
    retries: int = 3
    timeout_s: int = 10
    verbose: bool = False

    def __init__(
        self,
        url: str,
        auto_fetch: bool = False,
        retries: int = 3,
        timeout_s: int = 10,
        verbose: bool = False,
    ):
        super().__init__(verbose)
        self.url = url
        self.retries = retries
        self.timeout_s = timeout_s
        if auto_fetch:
            self.fetch_html()

    def fetch_html(self) -> Optional[str]:
        self.html = None  # reset value
        attempts = 0
        for _ in range(self.retries):
            try:
                response = requests.get(self.url, headers = HEADERS, timeout = self.timeout_s)
                response.raise_for_status()
                self.html = response.text
            except (RequestException, Timeout) as e:
                attempts += 1
                self.sprint(f"Error fetching HTML content: {e}. Retries left: {self.retries - attempts + 1}.")
                time.sleep(DEFAULT_SLEEP_S)
        return self.html
