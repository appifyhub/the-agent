import json

from langchain_core.tools import tool

from api.settings_controller import SettingsController
from db.crud.chat_config import ChatConfigCRUD
from db.crud.chat_message import ChatMessageCRUD
from db.crud.chat_message_attachment import ChatMessageAttachmentCRUD
from db.crud.price_alert import PriceAlertCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.tools_cache import ToolsCacheCRUD
from db.crud.user import UserCRUD
from db.sql import get_detached_session
from features.chat.announcement_manager import AnnouncementManager
from features.chat.attachments_content_resolver import AttachmentsContentResolver
from features.chat.generative_imaging_manager import GenerativeImagingManager
from features.chat.image_edit_manager import ImageEditManager
from features.chat.price_alert_manager import PriceAlertManager
from features.chat.sponsorship_manager import SponsorshipManager
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.chat.tools.base_tool_binder import BaseToolBinder
from features.currencies.exchange_rate_fetcher import ExchangeRateFetcher
from features.support.user_support_manager import UserSupportManager
from features.web_browsing.ai_web_search import AIWebSearch
from features.web_browsing.html_content_cleaner import HTMLContentCleaner
from features.web_browsing.web_fetcher import WebFetcher
from util.config import config
from util.safe_printer_mixin import sprint
from util.translations_cache import TranslationsCache

TOOL_TRUNCATE_LENGTH = 8192  # to save some tokens


@tool
def sponsor_friend(user_id: str, friend_telegram_username: str) -> str:
    """
    Sponsors a friend to use the chatbot.

    Args:
        user_id: A unique identifier of the user/author/sponsor, usually found in the metadata
        friend_telegram_username: [mandatory] The Telegram username of the friend to sponsor, without '@'
    """
    try:
        with get_detached_session() as db:
            sponsorship_manager = SponsorshipManager(UserCRUD(db), SponsorshipCRUD(db))
            result, message = sponsorship_manager.sponsor_user(user_id, friend_telegram_username)
            if result == SponsorshipManager.Result.failure:
                return json.dumps({"result": "Failure", "reason": message})
            return json.dumps({"result": "Success", "next_step": message})
    except Exception as e:
        sprint("Tool call failed", e)
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def unsponsor_friend(user_id: str, friend_telegram_username: str) -> str:
    """
    Revokes sponsorship for a friend from using the chatbot.

    Args:
        user_id: A unique identifier of the user/author/sponsor, usually found in the metadata
        friend_telegram_username: [mandatory] The Telegram username of the friend to un-sponsor, without '@'
    """
    try:
        with get_detached_session() as db:
            sponsorship_manager = SponsorshipManager(UserCRUD(db), SponsorshipCRUD(db))
            result, message = sponsorship_manager.unsponsor_user(user_id, friend_telegram_username)
            if result == SponsorshipManager.Result.failure:
                return json.dumps({"result": "Failure", "reason": message})
            return json.dumps({"result": "Success", "next_step": message})
    except Exception as e:
        sprint("Tool call failed", e)
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def process_attachments(
    chat_id: str,
    user_id: str,
    attachment_ids: str,
    operation: str = "describe",
    context: str | None = None,
) -> str:
    """
    Processes the contents of the given attachments. Allowed operations are:
        - 'describe' (default): Describes the image contents, transcribes audio, searches docs
        - 'edit-image': Edits the image based on the provided context (e.g. "Replace background with a space vortex")
        - 'remove-background': Removes the image background
        - 'restore-image': Restores an old/broken image (primarily faces)

    Args:
        chat_id: [mandatory] A unique identifier of the chat, usually found in the metadata
        user_id: [mandatory] A unique identifier of the user/author, usually found in the metadata
        attachment_ids: [mandatory] A comma-separated list of verbatim, unique 📎 attachment IDs that need to be resolved (located in each message); include any dashes, underscores or other symbols; these IDs are not to be cleaned or truncated
        operation: [mandatory] The action to perform on the attachments
        context: [optional] Additional task context or guidance, e.g. the user's message/question/caption, if available
    """
    try:
        operation = operation.lower().strip()
        editing_operations = ImageEditManager.Operation.values()
        allowed_operations = ["describe"] + editing_operations
        with get_detached_session() as db:
            if operation == "describe":
                # Resolve the attachments into text
                content_resolver = AttachmentsContentResolver(
                    chat_id = chat_id,
                    invoker_user_id_hex = user_id,
                    additional_context = context,
                    attachment_ids = attachment_ids.split(','),
                    bot_sdk = TelegramBotSDK(db),
                    user_dao = UserCRUD(db),
                    chat_config_dao = ChatConfigCRUD(db),
                    chat_message_dao = ChatMessageCRUD(db),
                    chat_message_attachment_dao = ChatMessageAttachmentCRUD(db),
                    cache_dao = ToolsCacheCRUD(db),
                )
                result = content_resolver.execute()
                if result == AttachmentsContentResolver.Result.failed:
                    raise ValueError("Failed to resolve attachments")
                return json.dumps({"result": result.value, "attachments": content_resolver.resolution_result})
            elif operation in editing_operations:
                manager = ImageEditManager(
                    chat_id = chat_id,
                    attachment_ids = attachment_ids.split(','),
                    invoker_user_id_hex = user_id,
                    operation_name = operation,
                    operation_guidance = context,
                    bot_sdk = TelegramBotSDK(db),
                    user_dao = UserCRUD(db),
                    chat_message_attachment_dao = ChatMessageAttachmentCRUD(db),
                )
                result, stats = manager.execute()
                if result == ImageEditManager.Result.failed:
                    raise ValueError("Failed to edit the images")
                return json.dumps(
                    {
                        "result": result.value,
                        "stats": stats,
                        "next_step": "Relay this status update to the partner",
                    }
                )
            else:
                # Unknown operation, must report back
                raise ValueError(f"Unknown operation '{operation}'; try one of: [{', '.join(allowed_operations)}]")
    except Exception as e:
        sprint("Tool call failed", e)
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def fetch_web_content(url: str) -> str:
    """
    Fetches the text content from the given web page URL.

    Args:
        url: [mandatory] A valid URL of the web page, starting with 'http://' or 'https://' provided in the text
    """
    try:
        with get_detached_session() as db:
            tools_cache_dao = ToolsCacheCRUD(db)
            html = WebFetcher(url, tools_cache_dao, auto_fetch_html = True).html
            text = HTMLContentCleaner(str(html), tools_cache_dao).clean_up()
            result = text[:TOOL_TRUNCATE_LENGTH] + '...' if len(text) > TOOL_TRUNCATE_LENGTH else text
            return json.dumps({"result": "Success", "content": result})
    except Exception as e:
        sprint("Tool call failed", e)
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
            fetcher = ExchangeRateFetcher(user_id, UserCRUD(db), ToolsCacheCRUD(db))
            result = fetcher.execute(base_currency, desired_currency, amount or 1.0)
            return json.dumps({"result": "Success", "exchange_rate": result})
    except Exception as e:
        sprint("Tool call failed", e)
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
        sprint("Tool call failed", e)
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
        sprint("Tool call failed", e)
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
        sprint("Tool call failed", e)
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
            imaging = GenerativeImagingManager(chat_id, prompt, user_id, TelegramBotSDK(db), UserCRUD(db))
            result = imaging.execute()
            if result == GenerativeImagingManager.Result.failed:
                raise ValueError("Failed to generate the image")
        return json.dumps({"result": "Success", "next_step": "Confirm to partner that the image has been sent"})
    except Exception as e:
        sprint("Tool call failed", e)
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def ai_web_search(user_id: str, search_query: str) -> str:
    """
    Searches the web for the given query, and responds using AI.

    Args:
        user_id: [mandatory] A unique identifier of the user/author, usually found in the metadata
        search_query: [mandatory] The user's search query, in English
    """
    try:
        with get_detached_session() as db:
            search = AIWebSearch(user_id, search_query, UserCRUD(db))
            result = search.execute()
            if not result.content:
                raise ValueError("Answer not received")
            return json.dumps({"result": "Success", "content": result.content})
    except Exception as e:
        sprint("Tool call failed", e)
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def announce_maintenance_or_news(user_id: str, raw_announcement: str) -> str:
    """
    [Developers-only] Announces a maintenance or news message from developers to all chats.

    Args:
        user_id: [mandatory] A unique identifier of the user/author, usually found in the metadata
        raw_announcement: [mandatory] The raw announcement message to send to all chats
    """
    try:
        with get_detached_session() as db:
            manager = AnnouncementManager(
                invoker_user_id_hex = user_id,
                raw_message = raw_announcement,
                translations = TranslationsCache(),
                telegram_bot_sdk = TelegramBotSDK(db),
                user_dao = UserCRUD(db),
                chat_config_dao = ChatConfigCRUD(db),
                chat_message_dao = ChatMessageCRUD(db),
            )
            results = manager.execute()
            return json.dumps(
                {
                    "result": "Success",
                    "summary": results,
                    "next_step": "Report these summary numbers back to the developer-user",
                }
            )
    except Exception as e:
        sprint("Tool call failed", e)
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def deliver_message(author_user_id: str, message: str, target_telegram_username: str) -> str:
    """
    [Developers-only] Delivers a personalized message from developers to a specific user.

    Args:
        author_user_id: [mandatory] A unique identifier of the user/author, usually found in the metadata
        message: [mandatory] The message to deliver to the target user
        target_telegram_username: [mandatory] Telegram username of the target user to send the message to, without '@'
    """
    try:
        with get_detached_session() as db:
            manager = AnnouncementManager(
                invoker_user_id_hex = author_user_id,
                raw_message = message,
                translations = TranslationsCache(),
                telegram_bot_sdk = TelegramBotSDK(db),
                user_dao = UserCRUD(db),
                chat_config_dao = ChatConfigCRUD(db),
                chat_message_dao = ChatMessageCRUD(db),
                target_telegram_username = target_telegram_username,
            )
            results = manager.execute()
            return json.dumps(
                {
                    "result": "Success",
                    "summary": results,
                    "next_step": "Report these summary numbers back to the developer-user",
                }
            )
    except Exception as e:
        sprint("Tool call failed", e)
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def request_feature_bug_or_support(
    author_user_id: str,
    user_request_details: str,
    request_type: str | None = None,
    include_full_name: bool = False,
    include_telegram_username: bool = False,
    author_github_username: str | None = None,
) -> str:
    """
    Allows the user to request a feature, report a bug, or ask for support. As a result, a GitHub issue is created.
    You are allowed to converse with the user to gather more details (based on this function arguments) before creating.
    Make sure to explicitly call this function once the user is ready to submit the request.

    Args:
        author_user_id: [mandatory] A unique identifier of the user/author, usually found in the metadata
        user_request_details: [mandatory] The user's request, bug report, or support question
        include_full_name: [mandatory] Whether to include the user's full name in the GitHub issue
        include_telegram_username: [mandatory] Whether to include the user's Telegram username in the GitHub issue
        request_type: [optional] The type of the request: [ 'feature', 'bug', 'request' ]
        author_github_username: [optional] The GitHub username of the author, if available and shared
    """
    try:
        with get_detached_session() as db:
            manager = UserSupportManager(
                invoker_user_id_hex = author_user_id,
                user_input = user_request_details,
                invoker_github_username = author_github_username,
                include_telegram_username = include_telegram_username,
                include_full_name = include_full_name,
                request_type_str = request_type,
                user_dao = UserCRUD(db),
            )
            issue_url = manager.execute()
            return json.dumps(
                {
                    "result": "Success",
                    "github_issue_url": issue_url,
                    "next_step": "Report this resolution back to the partner",
                }
            )
    except Exception as e:
        sprint("Tool call failed", e)
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def configure_settings(
    author_user_id: str,
    raw_settings_type: str,
    chat_id: str | None = None,
) -> str:
    """
    Launches the configuration screen. Configurations allow various profile settings, payments, API tokens/keys,
    current chat's settings, language, response rate, release notifications, model options, etc. Profile settings also
    serve as the initial setup for the agent (bot). In private chats, user settings are the default. The user will
    probably not know which settings they need, so you must choose for them or ask them.

    Args:
        author_user_id: [mandatory] A unique identifier of the user/author, usually found in the metadata
        raw_settings_type: [mandatory] The type of settings the user wants: [ 'user', 'chat' ]
        chat_id: [optional] A unique identifier of the chat to be configured, usually found in the metadata
    """
    try:
        with get_detached_session() as db:
            telegram_sdk = TelegramBotSDK(db)
            manager = SettingsController(
                invoker_user_id_hex = author_user_id,
                telegram_sdk = telegram_sdk,
                user_dao = UserCRUD(db),
                chat_config_dao = ChatConfigCRUD(db),
                sponsorship_dao = SponsorshipCRUD(db),
            )
            settings_link = manager.create_settings_link(
                raw_settings_type = raw_settings_type,
                target_chat_id = chat_id,
            )
            # let's send the settings link to the user's private chat, for security and privacy reasons
            destination_chat_id = manager.invoker_user.telegram_chat_id
            if not destination_chat_id:
                return json.dumps(
                    {
                        "result": "Error",
                        "error": "Author has no private chat with the bot; cannot send settings link",
                    }
                )
            telegram_sdk.send_button_link(destination_chat_id, settings_link)
            next_step: str
            if chat_id and chat_id == str(manager.invoker_user.telegram_chat_id or 0):
                next_step = "Notify the user that the link is just above; click it to configure your settings"
            else:
                next_step = "Notify the user that the link was sent to their private chat"
            return json.dumps(
                {
                    "result": "Success",
                    "next_step": next_step,
                }
            )
    except Exception as e:
        sprint("Tool call failed", e)
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def get_version() -> str:
    """
    Checks the current version of the bot (the latest version available to the users).
    """
    try:
        return json.dumps(
            {
                "result": "Success",
                "version": f"v{config.version}",
                "next_step": "Notify the user of the current (latest) version",
            }
        )
    except Exception as e:
        sprint("Tool call failed", e)
        return json.dumps({"result": "Error", "error": str(e)})


class ToolsLibrary(BaseToolBinder):

    def __init__(self):
        super().__init__(
            {
                "sponsor_friend": sponsor_friend,
                "unsponsor_friend": unsponsor_friend,
                "fetch_web_content": fetch_web_content,
                "process_attachments": process_attachments,
                "get_exchange_rate": get_exchange_rate,
                "set_up_currency_price_alert": set_up_currency_price_alert,
                "remove_currency_price_alerts": remove_currency_price_alerts,
                "list_currency_price_alerts": list_currency_price_alerts,
                "generate_image": generate_image,
                "ai_web_search": ai_web_search,
                "announce_maintenance_or_news": announce_maintenance_or_news,
                "deliver_message": deliver_message,
                "request_feature_bug_or_support": request_feature_bug_or_support,
                "configure_settings": configure_settings,
                "get_version": get_version,
            }
        )
