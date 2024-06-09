import httpx

from chat.telegram.model.attachment.file import File
from util.config import Config
from util.safe_printer_mixin import SafePrinterMixin


class BotAPI(SafePrinterMixin):
    """https://core.telegram.org/bots/api"""
    __bot_api_url: str
    __config: Config

    def __init__(self, config: Config):
        super().__init__(config.verbose)
        self.__bot_api_url = f"{config.telegram_api_base_url}/bot{config.telegram_bot_token}"
        self.__config = config

    def get_file_info(self, file_id: str) -> File:
        self.sprint(f"Getting file info for file_id: {file_id}")
        url = f"{self.__bot_api_url}/getFile"
        response = httpx.get(url, params = {"file_id": file_id})
        response.raise_for_status()
        return File(**response.json())
