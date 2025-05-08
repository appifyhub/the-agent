import time
from typing import Literal

from sqlalchemy.orm import Session

from db.schema.chat_message import ChatMessage
from features.chat.telegram.model.chat_member import ChatMember
from features.chat.telegram.model.message import Message
from features.chat.telegram.model.update import Update
from features.chat.telegram.sdk.telegram_bot_api import TelegramBotAPI
from features.chat.telegram.telegram_data_resolver import TelegramDataResolver
from features.chat.telegram.telegram_domain_mapper import TelegramDomainMapper
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


class TelegramBotSDK(SafePrinterMixin):
    _db: Session
    api: TelegramBotAPI

    def __init__(
        self,
        db: Session,
        override_bot_api: TelegramBotAPI | None = None,
    ):
        super().__init__(config.verbose)
        self._db = db
        self.api = override_bot_api or TelegramBotAPI()

    def send_text_message(
        self,
        chat_id: int | str,
        text: str,
        parse_mode: str = "markdown",
        disable_notification: bool = False,
        link_preview_options: dict = None,
    ) -> ChatMessage:
        sent_message = self.api.send_text_message(
            chat_id = chat_id,
            text = text,
            parse_mode = parse_mode,
            disable_notification = disable_notification,
            link_preview_options = link_preview_options,
        )
        return self.__store_api_response_as_message(sent_message)

    def send_photo(
        self,
        chat_id: int | str,
        photo_url: str,
        caption: str | None = None,
        parse_mode: str = "markdown",
        disable_notification: bool = False,
    ) -> ChatMessage:
        sent_message = self.api.send_photo(
            chat_id = chat_id,
            photo_url = photo_url,
            caption = caption,
            parse_mode = parse_mode,
            disable_notification = disable_notification,
        )
        return self.__store_api_response_as_message(sent_message)

    def send_document(
        self,
        chat_id: int | str,
        document_url: str,
        parse_mode: str = "markdown",
        thumbnail: str | None = None,
        caption: str | None = None,
        disable_notification: bool = False,
    ) -> ChatMessage:
        sent_message = self.api.send_document(
            chat_id = chat_id,
            document_url = document_url,
            caption = caption,
            parse_mode = parse_mode,
            thumbnail = thumbnail,
            disable_notification = disable_notification,
        )
        return self.__store_api_response_as_message(sent_message)

    def set_status_typing(self, chat_id: int | str):
        self.api.set_status_typing(chat_id)

    def set_status_uploading_image(self, chat_id: int | str):
        self.api.set_status_uploading_image(chat_id)

    def set_reaction(self, chat_id: int | str, message_id: int | str, reaction: str | None):
        self.api.set_reaction(chat_id = chat_id, message_id = message_id, reaction = reaction)

    def send_button_link(
        self,
        chat_id: int | str,
        link_url: str,
        url_type: Literal["user_settings", "chat_settings"]
    ) -> ChatMessage:
        sent_message = self.api.send_button_link(chat_id, link_url, url_type)
        return self.__store_api_response_as_message(sent_message)

    def get_chat_member(self, chat_id: int | str, user_id: int | str) -> ChatMember | None:
        try:
            return self.api.get_chat_member(chat_id, user_id)
        except Exception as e:
            self.sprint(f"Failed to get chat member '{user_id}' from chat '{chat_id}'", e)
            return None

    def __store_api_response_as_message(self, raw_api_response: dict) -> ChatMessage:
        self.sprint("Storing API message data...")
        message = Message(**raw_api_response["result"])
        update = Update(update_id = time.time_ns(), message = message)
        mapping_result = TelegramDomainMapper().map_update(update)
        if not mapping_result:
            raise ValueError(f"Telegram API domain mapping failed for local update '{update.update_id}'")
        # noinspection PyProtectedMember
        data_resolver = TelegramDataResolver(self._db, self.api)
        resolution_result = data_resolver.resolve(mapping_result)
        if not resolution_result.message:
            raise ValueError(f"Telegram data resolution failed for local update '{update.update_id}'")
        # noinspection PyTypeChecker
        return resolution_result.message
