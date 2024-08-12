import re

import requests

from features.chat.telegram.model.attachment.file import File
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


class TelegramBotAPI(SafePrinterMixin):
    """https://core.telegram.org/bots/api"""
    __bot_api_url: str

    def __init__(self):
        super().__init__(config.verbose)
        self.__bot_api_url = f"{config.telegram_api_base_url}/bot{config.telegram_bot_token}"

    def get_file_info(self, file_id: str) -> File:
        self.sprint(f"Getting file info for file_id: {file_id}")
        url = f"{self.__bot_api_url}/getFile"
        response = requests.get(url, params = {"file_id": file_id})
        response.raise_for_status()
        return File(**response.json()["result"])

    def send_text_message(
        self,
        chat_id: int | str,
        text: str,
        parse_mode: str = "markdown",
        disable_notification: bool = False,
        link_preview_options: dict = None,
    ) -> dict:
        self.sprint(f"Sending message to chat #{chat_id}")
        url = f"{self.__bot_api_url}/sendMessage"
        cleaned_text = re.sub(r'(?<!\b)_(?!\b)', r'\\_', text)
        if link_preview_options is None:
            link_preview_options = {
                "is_disabled": False,
                "prefer_small_media": True,
                "show_above_text": True,
            }
        payload = {
            "chat_id": chat_id,
            "text": cleaned_text,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification,
            "link_preview_options": link_preview_options,
        }
        response = requests.post(url, json = payload, timeout = config.web_timeout_s)
        response.raise_for_status()
        return response.json()
