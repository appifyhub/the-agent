from typing import Literal

from db.model.chat_config import ChatConfigDB
from db.schema.chat_message import ChatMessage
from db.schema.chat_message_attachment import ChatMessageAttachment
from di.di import DI


class PlatformBotSDK:

    __di: DI

    def __init__(self, di: DI):
        self.__di = di

    def send_text_message(
        self,
        chat_id: int | str,
        text: str,
    ) -> ChatMessage:
        match self.__di.require_invoker_chat_type():
            case ChatConfigDB.ChatType.telegram:
                return self.__di.telegram_bot_sdk.send_text_message(chat_id, text)
            case ChatConfigDB.ChatType.whatsapp:
                return self.__di.whatsapp_bot_sdk.send_text_message(chat_id, text)
            case _:
                raise ValueError(f"Unsupported chat type: {self.__di.require_invoker_chat_type()}")

    def send_photo(
        self,
        chat_id: int | str,
        photo_url: str,
        caption: str | None = None,
    ) -> ChatMessage:
        match self.__di.require_invoker_chat_type():
            case ChatConfigDB.ChatType.telegram:
                return self.__di.telegram_bot_sdk.send_photo(chat_id, photo_url, caption)
            case ChatConfigDB.ChatType.whatsapp:
                return self.__di.whatsapp_bot_sdk.send_photo(chat_id, photo_url, caption)
            case _:
                raise ValueError(f"Unsupported chat type: {self.__di.require_invoker_chat_type()}")

    def send_document(
        self,
        chat_id: int | str,
        document_url: str,
        caption: str | None = None,
        thumbnail: str | None = None,
    ) -> ChatMessage:
        match self.__di.require_invoker_chat_type():
            case ChatConfigDB.ChatType.telegram:
                return self.__di.telegram_bot_sdk.send_document(
                    chat_id = chat_id,
                    document_url = document_url,
                    thumbnail = thumbnail,
                    caption = caption,
                )
            case ChatConfigDB.ChatType.whatsapp:
                return self.__di.whatsapp_bot_sdk.send_document(chat_id, document_url, caption)
            case _:
                raise ValueError(f"Unsupported chat type: {self.__di.require_invoker_chat_type()}")

    def send_button_link(
        self,
        chat_id: int | str,
        link_url: str,
        button_text: str = "⚙️",
    ) -> ChatMessage:
        match self.__di.require_invoker_chat_type():
            case ChatConfigDB.ChatType.telegram:
                return self.__di.telegram_bot_sdk.send_button_link(chat_id, link_url, button_text)
            case ChatConfigDB.ChatType.whatsapp:
                return self.__di.whatsapp_bot_sdk.send_button_link(chat_id, link_url, button_text)
            case _:
                raise ValueError(f"Unsupported chat type: {self.__di.require_invoker_chat_type()}")

    def set_reaction(
        self,
        chat_id: int | str,
        message_id: int | str,
        reaction: str | None,
    ) -> None:
        match self.__di.require_invoker_chat_type():
            case ChatConfigDB.ChatType.telegram:
                self.__di.telegram_bot_sdk.set_reaction(chat_id, message_id, reaction)
            case ChatConfigDB.ChatType.whatsapp:
                self.__di.whatsapp_bot_sdk.set_reaction(chat_id, message_id, reaction)
            case _:
                raise ValueError(f"Unsupported chat type: {self.__di.require_invoker_chat_type()}")

    def set_chat_action(
        self,
        chat_id: int | str,
        action: Literal["typing", "upload_photo"],
    ) -> None:
        match self.__di.require_invoker_chat_type():
            case ChatConfigDB.ChatType.telegram:
                self.__di.telegram_bot_sdk.set_chat_action(chat_id, action)
            case ChatConfigDB.ChatType.whatsapp:
                pass  # WhatsApp doesn't support chat actions (typing indicators)
            case _:
                raise ValueError(f"Unsupported chat type: {self.__di.require_invoker_chat_type()}")

    def refresh_attachments_by_ids(
        self,
        attachment_ids: list[str],
    ) -> list[ChatMessageAttachment]:
        match self.__di.require_invoker_chat_type():
            case ChatConfigDB.ChatType.telegram:
                return self.__di.telegram_bot_sdk.refresh_attachments_by_ids(attachment_ids)
            case ChatConfigDB.ChatType.whatsapp:
                return self.__di.whatsapp_bot_sdk.refresh_attachments_by_ids(attachment_ids)
            case _:
                raise ValueError(f"Unsupported chat type: {self.__di.require_invoker_chat_type()}")

    def refresh_attachment_instances(
        self,
        attachments: list[ChatMessageAttachment],
    ) -> list[ChatMessageAttachment]:
        match self.__di.require_invoker_chat_type():
            case ChatConfigDB.ChatType.telegram:
                return self.__di.telegram_bot_sdk.refresh_attachment_instances(attachments)
            case ChatConfigDB.ChatType.whatsapp:
                return self.__di.whatsapp_bot_sdk.refresh_attachment_instances(attachments)
            case _:
                raise ValueError(f"Unsupported chat type: {self.__di.require_invoker_chat_type()}")
