import json
import traceback

from langchain_core.tools import tool

from db.crud.chat_config import ChatConfigCRUD
from db.crud.chat_message import ChatMessageCRUD
from db.crud.chat_message_attachment import ChatMessageAttachmentCRUD
from db.crud.invite import InviteCRUD
from db.crud.price_alert import PriceAlertCRUD
from db.crud.tools_cache import ToolsCacheCRUD
from db.crud.user import UserCRUD
from db.sql import get_detached_session
from features.chat.attachments_content_resolver import AttachmentsContentResolver
from features.chat.chat_config_manager import ChatConfigManager
from features.chat.invite_manager import InviteManager
from features.chat.telegram.telegram_bot_api import TelegramBotAPI
from features.chat.tools.base_tool_binder import BaseToolBinder
from features.currencies.exchange_rate_fetcher import ExchangeRateFetcher
from features.currencies.price_alert_manager import PriceAlertManager
from features.images.generative_imaging_manager import GenerativeImagingManager
from features.web_browsing.html_content_cleaner import HTMLContentCleaner
from features.web_browsing.web_fetcher import WebFetcher

TOOL_TRUNCATE_LENGTH = 8192  # to save some tokens


@tool
def invite_friend(user_id: str, friend_telegram_username: str) -> str:
    """
    Invites a friend to the chatbot.

    Args:
        user_id: A unique identifier of the user/author, usually found in the metadata
        friend_telegram_username: [mandatory] The Telegram username of the friend to invite, without '@'
    """
    try:
        with get_detached_session() as db:
            invite_manager = InviteManager(UserCRUD(db), InviteCRUD(db))
            result, message = invite_manager.invite_user(user_id, friend_telegram_username)
            if result == InviteManager.Result.failure:
                return json.dumps({"result": "Failure", "reason": message})
            return json.dumps({"result": "Success", "next_step": message})
    except Exception as e:
        traceback.print_exc()
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def uninvite_friend(user_id: str, friend_telegram_username: str) -> str:
    """
    Uninvites a friend from the chatbot.

    Args:
        user_id: A unique identifier of the user/author, usually found in the metadata
        friend_telegram_username: [mandatory] The Telegram username of the friend to uninvite, without '@'
    """
    try:
        with get_detached_session() as db:
            invite_manager = InviteManager(UserCRUD(db), InviteCRUD(db))
            result, message = invite_manager.uninvite_user(user_id, friend_telegram_username)
            if result == InviteManager.Result.failure:
                return json.dumps({"result": "Failure", "reason": message})
            return json.dumps({"result": "Success", "next_step": message})
    except Exception as e:
        traceback.print_exc()
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def change_chat_language(chat_id: str, language_name: str, language_iso_code: str | None = None) -> str:
    """
    Changes the chat's main language, whether directly or indirectly requested by a user.

    Args:
        chat_id: [mandatory] A unique identifier of the chat, usually found in the metadata
        language_name: [mandatory] The name of the preferred language, in English
        language_iso_code: [optional] The 2-character ISO code of the preferred language, if known
    """
    try:
        with get_detached_session() as db:
            chat_config_manager = ChatConfigManager(ChatConfigCRUD(db))
            result, message = chat_config_manager.change_chat_language(chat_id, language_name, language_iso_code)
            if result == ChatConfigManager.Result.failure:
                return json.dumps({"result": "Failure", "reason": message})
            return json.dumps({"result": "Success", "message": message, "next_step": "Notify the user"})
    except Exception as e:
        traceback.print_exc()
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def change_chat_reply_chance(chat_id: str, reply_chance_percent: int) -> str:
    """
    Changes the bot's chance (in percent) to reply to this chat.

    Args:
        chat_id: [mandatory] A unique identifier of the chat, usually found in the metadata
        reply_chance_percent: [mandatory] The chance, in percent [0-100], for the bot to reply to this chat
    """
    try:
        with get_detached_session() as db:
            chat_config_manager = ChatConfigManager(ChatConfigCRUD(db))
            result, message = chat_config_manager.change_chat_reply_chance(chat_id, reply_chance_percent)
            if result == ChatConfigManager.Result.failure:
                return json.dumps({"result": "Failure", "reason": message})
            return json.dumps({"result": "Success", "message": message, "next_step": "Notify the user"})
    except Exception as e:
        traceback.print_exc()
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def resolve_attachments(chat_id: str, user_id: str, attachment_ids: str, context: str | None = None) -> str:
    """
    Resolves the contents of the given attachments into text, e.g. analyzing a photo, audio, etc.

    Args:
        chat_id: [mandatory] A unique identifier of the chat, usually found in the metadata
        user_id: [mandatory] A unique identifier of the user/author, usually found in the metadata
        attachment_ids: [mandatory] A comma-separated list of unique 📎 attachment IDs that need to be resolved (located in each message)
        context: [optional] Additional context translated to English, e.g. the user's message/question, if available
    """
    try:
        with get_detached_session() as db:
            attachments_content_resolver = AttachmentsContentResolver(
                chat_id = chat_id,
                invoker_user_id_hex = user_id,
                additional_context = context,
                attachment_ids = attachment_ids.split(','),
                bot_api = TelegramBotAPI(),
                user_dao = UserCRUD(db),
                chat_config_dao = ChatConfigCRUD(db),
                chat_message_dao = ChatMessageCRUD(db),
                chat_message_attachment_dao = ChatMessageAttachmentCRUD(db),
                cache_dao = ToolsCacheCRUD(db),
            )
            status = attachments_content_resolver.execute()
            if status == AttachmentsContentResolver.Result.failed:
                raise ValueError("Failed to resolve attachments")
            return json.dumps(
                {
                    "result": status.value,
                    "attachments": attachments_content_resolver.resolution_result,
                }
            )
    except Exception as e:
        traceback.print_exc()
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def fetch_web_content(url: str) -> str:
    """
    Fetches the text content from the given web page URL.

    Args:
        url: [mandatory] A valid URL of the web page, starting with 'http://' or 'https://'
    """
    try:
        with get_detached_session() as db:
            tools_cache_dao = ToolsCacheCRUD(db)
            html = WebFetcher(url, tools_cache_dao, auto_fetch_html = True).html
            text = HTMLContentCleaner(str(html), tools_cache_dao).clean_up()
            result = text[:TOOL_TRUNCATE_LENGTH] + '...' if len(text) > TOOL_TRUNCATE_LENGTH else text
            return json.dumps({"result": "Success", "content": result})
    except Exception as e:
        traceback.print_exc()
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def get_exchange_rate(user_id: str, base_currency: str, desired_currency: str, amount: str | None = None) -> str:
    """
    Fetches the exchange rate between two (crypto or fiat) currencies.

    Args:
        user_id: [mandatory] A unique identifier of the user/author, usually found in the metadata
        base_currency: [mandatory] The currency code of the base currency, e.g. 'USD' or 'BTC'
        desired_currency: [mandatory] The currency code of the desired currency, e.g. 'EUR' or 'ADA'
        amount: [optional] The amount of the base currency to convert; not sending this will assume value of 1.0
    """
    try:
        with get_detached_session() as db:
            user_dao = UserCRUD(db)
            fetcher = ExchangeRateFetcher(user_id, user_dao, ToolsCacheCRUD(db))
            result = fetcher.execute(base_currency, desired_currency, amount or 1.0)
            return json.dumps({"result": "Success", "exchange_rate": result})
    except Exception as e:
        traceback.print_exc()
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def set_up_currency_price_alert(
    chat_id: str, user_id: str, base_currency: str, desired_currency: str, threshold_percent: int,
) -> str:
    """
    Sets up a price alert at the given threshold for the given currency pair.

    Args:
        chat_id: [mandatory] A unique identifier of the chat, usually found in the metadata
        user_id: [mandatory] A unique identifier of the user/author, usually found in the metadata
        base_currency: [mandatory] The currency code of the base currency, e.g. 'USD' or 'BTC'
        desired_currency: [mandatory] The currency code of the desired currency, e.g. 'EUR' or 'ADA'
        threshold_percent: [mandatory] The trigger threshold, in percent [0-100], that triggers the price alert
    """
    try:
        with get_detached_session() as db:
            user_dao = UserCRUD(db)
            fetcher = ExchangeRateFetcher(user_id, user_dao, ToolsCacheCRUD(db))
            alert_manager = PriceAlertManager(
                chat_id, user_id, user_dao, ChatConfigCRUD(db), PriceAlertCRUD(db), fetcher,
            )
            alert = alert_manager.create_alert(base_currency, desired_currency, threshold_percent)
            return json.dumps({"result": "Success", "created_alert_data": alert.model_dump()})
    except Exception as e:
        traceback.print_exc()
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def remove_currency_price_alerts(chat_id: str, user_id: str, base_currency: str, desired_currency: str) -> str:
    """
    Deletes the oldest price alert for the given currency pair.

    Args:
        chat_id: [mandatory] A unique identifier of the chat, usually found in the metadata
        user_id: [mandatory] A unique identifier of the user/author, usually found in the metadata
        base_currency: [mandatory] The currency code of the base currency, e.g. 'USD' or 'BTC'
        desired_currency: [mandatory] The currency code of the desired currency, e.g. 'EUR' or 'ADA'
    """
    try:
        with get_detached_session() as db:
            user_dao = UserCRUD(db)
            fetcher = ExchangeRateFetcher(user_id, user_dao, ToolsCacheCRUD(db))
            alert_manager = PriceAlertManager(
                chat_id, user_id, user_dao, ChatConfigCRUD(db), PriceAlertCRUD(db), fetcher,
            )
            alert = alert_manager.delete_alert(base_currency, desired_currency)
            return json.dumps({"result": "Success", "deleted_alert_data": alert.model_dump()})
    except Exception as e:
        traceback.print_exc()
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def list_currency_price_alerts(chat_id: str, user_id: str) -> str:
    """
    Lists all price alerts.

    Args:
        chat_id: [mandatory] A unique identifier of the chat, usually found in the metadata
        user_id: [mandatory] A unique identifier of the user/author, usually found in the metadata
    """
    try:
        with get_detached_session() as db:
            user_dao = UserCRUD(db)
            fetcher = ExchangeRateFetcher(user_id, user_dao, ToolsCacheCRUD(db))
            alert_manager = PriceAlertManager(
                chat_id, user_id, user_dao, ChatConfigCRUD(db), PriceAlertCRUD(db), fetcher,
            )
            alerts = alert_manager.get_all_alerts()
            return json.dumps({"result": "Success", "alerts": [alert.model_dump() for alert in alerts]})
    except Exception as e:
        traceback.print_exc()
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def generate_image(chat_id: str, user_id: str, prompt: str) -> str:
    """
    Generates an image based on the given prompt using Generative AI.

    Args:
        chat_id: [mandatory] A unique identifier of the chat, usually found in the metadata
        user_id: [mandatory] A unique identifier of the user/author, usually found in the metadata
        prompt: [mandatory] The user's description or prompt for the generated image
    """
    try:
        with get_detached_session() as db:
            imaging = GenerativeImagingManager(chat_id, prompt, user_id, TelegramBotAPI(), UserCRUD(db))
            result = imaging.execute()
            if result == GenerativeImagingManager.Result.failed:
                raise ValueError("Failed to generate the image")
        return json.dumps({"result": "Success", "next_step": "Confirm to partner that the image has been sent"})
    except Exception as e:
        traceback.print_exc()
        return json.dumps({"result": "Error", "error": str(e)})


class ToolsLibrary(BaseToolBinder):

    def __init__(self):
        super().__init__(
            {
                "invite_friend": invite_friend,
                "uninvite_friend": uninvite_friend,
                "change_chat_language": change_chat_language,
                "change_chat_reply_chance": change_chat_reply_chance,
                "fetch_web_content": fetch_web_content,
                "resolve_attachments": resolve_attachments,
                "get_exchange_rate": get_exchange_rate,
                "set_up_currency_price_alert": set_up_currency_price_alert,
                "remove_currency_price_alerts": remove_currency_price_alerts,
                "list_currency_price_alerts": list_currency_price_alerts,
                "generate_image": generate_image,
            }
        )
