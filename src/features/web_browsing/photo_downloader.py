import requests

from util import log
from util.config import config
from util.error_codes import WEB_FETCH_FAILED
from util.errors import ExternalServiceError


class PhotoDownloader:

    __bearer_token: str | None

    def __init__(self, bearer_token: str | None = None):
        self.__bearer_token = bearer_token

    def download(self, url: str) -> bytes | None:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; AppifyHub-Agent/1.0)"}
            if self.__bearer_token:
                headers["Authorization"] = f"Bearer {self.__bearer_token}"
            response = requests.get(url, headers = headers, timeout = config.web_timeout_s)
            response.raise_for_status()
            return response.content
        except Exception as e:
            log.w(f"Failed to download photo from {url}", e)
            return None

    def download_many(self, urls: list[str]) -> list[bytes]:
        results = []
        for url in urls:
            data = self.download(url)
            if data:
                results.append(data)
        return results

    def require(self, url: str) -> bytes:
        data = self.download(url)
        if not data:
            raise ExternalServiceError(f"Failed to download required photo: {url}", WEB_FETCH_FAILED)
        return data
