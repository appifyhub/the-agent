import json
import re

import requests
from requests import Response, RequestException

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
        self.__raise_for_status(response)
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
        self.__raise_for_status(response)
        return response.json()

    def send_photo(
        self,
        chat_id: int | str,
        photo_url: str,
        caption: str | None = None,
        parse_mode: str = "markdown",
        disable_notification: bool = False,
    ) -> dict:
        self.sprint(f"Sending photo to chat #{chat_id}")
        url = f"{self.__bot_api_url}/sendPhoto"
        payload = {
            "chat_id": chat_id,
            "photo": photo_url,
            "disable_notification": disable_notification,
        }
        if caption:
            payload["caption"] = re.sub(r'(?<!\b)_(?!\b)', r'\\_', caption)
            payload["parse_mode"] = parse_mode
        response = requests.post(url, json = payload, timeout = config.web_timeout_s)
        self.__raise_for_status(response)
        return response.json()

    def send_document(
        self,
        chat_id: int | str,
        document_url: str,
        parse_mode: str = "markdown",
        thumbnail: str | None = None,
        caption: str | None = None,
        disable_notification: bool = False,
    ) -> dict:
        self.sprint(f"Sending document to chat #{chat_id}")
        url = f"{self.__bot_api_url}/sendDocument"
        payload = {
            "chat_id": chat_id,
            "document": document_url,
            "disable_notification": disable_notification,
        }
        if thumbnail:
            payload["thumbnail"] = thumbnail
        if caption:
            payload["caption"] = re.sub(r'(?<!\b)_(?!\b)', r'\\_', caption)
            payload["parse_mode"] = parse_mode
        response = requests.post(url, json = payload, timeout = config.web_timeout_s)
        self.__raise_for_status(response)
        return response.json()

    def set_status_typing(self, chat_id: int | str):
        url = f"{self.__bot_api_url}/sendChatAction"
        payload = {
            "chat_id": chat_id,
            "action": "typing",
        }
        response = requests.post(url, json = payload, timeout = config.web_timeout_s)
        self.__raise_for_status(response)
        return response.json()

    def set_status_uploading_image(self, chat_id: int | str):
        url = f"{self.__bot_api_url}/sendChatAction"
        payload = {
            "chat_id": chat_id,
            "action": "upload_photo",
        }
        response = requests.post(url, json = payload, timeout = config.web_timeout_s)
        self.__raise_for_status(response)
        return response.json()

    def set_reaction(self, chat_id: int | str, message_id: int | str, reaction: str | None):
        url = f"{self.__bot_api_url}/setMessageReaction"
        reactions_list = [{"type": "emoji", "emoji": reaction}] if reaction else []
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "reaction": reactions_list,
        }
        response = requests.post(url, json = payload, timeout = config.web_timeout_s)
        self.__raise_for_status(response)
        return response.json()

    def __raise_for_status(self, response: Response | None):
        if not response:
            message = "No API response received"
            self.sprint(f"  {message}")
            raise RequestException(message)
        if response.status_code != 200:
            self.sprint(f"  Status is not '200': HTTP_{response.status_code}!")
            self.sprint(json.dumps(response.json(), indent = 2))
            response.raise_for_status()
