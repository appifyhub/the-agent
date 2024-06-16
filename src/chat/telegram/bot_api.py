import httpx

from chat.telegram.model.attachment.file import File
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


class BotAPI(SafePrinterMixin):
    """https://core.telegram.org/bots/api"""
    __bot_api_url: str

    def __init__(self):
        super().__init__(config.verbose)
        self.__bot_api_url = f"{config.telegram_api_base_url}/bot{config.telegram_bot_token}"

    def get_file_info(self, file_id: str) -> File:
        self.sprint(f"Getting file info for file_id: {file_id}")
        url = f"{self.__bot_api_url}/getFile"
        response = httpx.get(url, params = {"file_id": file_id})
        response.raise_for_status()
        return File(**response.json())
