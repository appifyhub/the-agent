# ruff: noqa: E501

import json
from typing import Any

from langchain_core.tools import tool

from db.sql import get_detached_session
from di.di import DI
from features.chat.attachments_describer import AttachmentsDescriber
from features.chat.chat_imaging_service import ChatImagingService
from features.chat.dev_announcements_service import DevAnnouncementsService
from features.chat.llm_tools.base_llm_tool_binder import BaseLLMToolBinder
from features.chat.smart_stable_diffusion_generator import SmartStableDiffusionGenerator
from features.support.user_support_service import UserSupportService
from features.web_browsing.ai_web_search import AIWebSearch
from util.config import config
from util.safe_printer_mixin import sprint

TOOL_TRUNCATE_LENGTH = 8192  # to save some tokens


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
        attachment_ids: [mandatory] A comma-separated list of verbatim, unique 📎 attachment IDs that need to be processed (located in each message); include any dashes, underscores or other symbols; these IDs are not to be cleaned or truncated
        operation: [mandatory] The action to perform on the attachments
        context: [optional] Additional task context or guidance, e.g. the user's message/question/caption, if available
    """
    try:
        operation = operation.lower().strip()
        editing_operations = ChatImagingService.Operation.values()
        allowed_operations = ["describe"] + editing_operations
        with get_detached_session() as db:
            di = DI(db, user_id, chat_id)
            attachment_ids_list = attachment_ids.split(",")
            if operation == "describe":
                # Resolve the attachments into text
                describer = di.attachments_describer(context, attachment_ids_list)
                result = describer.execute()
                if result == AttachmentsDescriber.Result.failed:
                    raise ValueError("Failed to resolve attachments")
                return json.dumps({"result": result.value, "attachments": describer.result})
            elif operation in editing_operations:
                # Generate images based on the provided context
                result, details = di.chat_imaging_service(attachment_ids_list, operation, context).execute()
                if result == ChatImagingService.Result.failed:
                    raise ValueError("Failed to edit the images! Details: " + str(details))
                return __success({"status": result.value, "details": details, "next_step": "Deliver any errors to the partner"})
            else:
                # Unknown operation, must report back
                raise ValueError(f"Unknown operation '{operation}'; try one of: [{', '.join(allowed_operations)}]")
    except Exception as e:
        return __error(e)


@tool
def generate_image(chat_id: str, user_id: str, prompt: str) -> str:
    """
    Generates (draws) an image based on the given prompt using Generative AI.

    Args:
        chat_id: [mandatory] A unique identifier of the chat, usually found in the metadata
        user_id: [mandatory] A unique identifier of the user/author, usually found in the metadata
        prompt: [mandatory] The user's description or prompt for the generated image
    """
    try:
        with get_detached_session() as db:
            di = DI(db, user_id, chat_id)
            copywriter_tool = di.tool_choice_resolver.require_tool(
                SmartStableDiffusionGenerator.COPYWRITER_TOOL_TYPE,
                SmartStableDiffusionGenerator.DEFAULT_COPYWRITER_TOOL,
            )
            image_gen_tool = di.tool_choice_resolver.require_tool(
                SmartStableDiffusionGenerator.IMAGE_GEN_TOOL_TYPE,
                SmartStableDiffusionGenerator.DEFAULT_IMAGE_GEN_TOOL,
            )
            generator = di.smart_stable_diffusion_generator(prompt, copywriter_tool, image_gen_tool)
            result = generator.execute()
            if result == SmartStableDiffusionGenerator.Result.failed:
                raise ValueError(f"Failed to generate the image! Reason: {str(generator.error)}")
            return __success({"next_step": "Confirm to partner that the image has been sent"})
    except Exception as e:
        return __error(e)


@tool
def fetch_web_content(url: str, user_id: str) -> str:
    """
    Fetches the text content from the given web page URL.

    Args:
        url: [mandatory] A valid URL of the web page, starting with 'http://' or 'https://' provided in the text
        user_id: [mandatory] A unique identifier of the user/author, usually found in the metadata
    """
    try:
        with get_detached_session() as db:
            di = DI(db, user_id)
            fetcher = di.web_fetcher(url, auto_fetch_html = True)
            html = str(fetcher.html)
            text = di.html_content_cleaner(html).clean_up()
            result = text[:TOOL_TRUNCATE_LENGTH] + "..." if len(text) > TOOL_TRUNCATE_LENGTH else text
            return __success({"content": result})
    except Exception as e:
        return __error(e)


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
            di = DI(db, user_id)
            result = di.exchange_rate_fetcher.execute(base_currency, desired_currency, float(amount) if amount else 1.0)
            return __success({"exchange_rate": result})
    except Exception as e:
        return __error(e)


@tool
def set_up_currency_price_alert(
    chat_id: str,
    user_id: str,
    base_currency: str,
    desired_currency: str,
    threshold_percent: int,
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
            di = DI(db, user_id, chat_id)
            service = di.currency_alert_service(chat_id)
            alert = service.create_alert(base_currency, desired_currency, threshold_percent)
            return __success({"created_alert_data": alert.model_dump(mode = "json")})
    except Exception as e:
        return __error(e)


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
            di = DI(db, user_id, chat_id)
            service = di.currency_alert_service(chat_id)
            alert = service.delete_alert(base_currency, desired_currency)
            deleted_alert_data = alert.model_dump(mode = "json") if alert else None
            return __success({"deleted_alert_data": deleted_alert_data})
    except Exception as e:
        return __error(e)


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
            di = DI(db, user_id, chat_id)
            service = di.currency_alert_service(chat_id)
            alerts = service.get_active_alerts()
            return __success({"alerts": [alert.model_dump(mode = "json") for alert in alerts]})
    except Exception as e:
        return __error(e)


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
            di = DI(db, user_id)
            configured_tool = di.tool_choice_resolver.require_tool(AIWebSearch.TOOL_TYPE, AIWebSearch.DEFAULT_TOOL)
            search = di.ai_web_search(search_query, configured_tool)
            result = search.execute()
            if not result.content:
                raise ValueError("Answer not received")
            return __success({"content": result.content})
    except Exception as e:
        return __error(e)


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
            di = DI(db, user_id)
            configured_tool = di.tool_choice_resolver.require_tool(
                DevAnnouncementsService.TOOL_TYPE,
                DevAnnouncementsService.DEFAULT_TOOL,
            )
            results = di.dev_announcements_service(raw_announcement, None, configured_tool).execute()
            return __success(
                {
                    "summary": results,
                    "next_step": "Report these summary numbers back to the developer-user",
                },
            )
    except Exception as e:
        return __error(e)


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
            di = DI(db, author_user_id)
            configured_tool = di.tool_choice_resolver.require_tool(
                DevAnnouncementsService.TOOL_TYPE,
                DevAnnouncementsService.DEFAULT_TOOL,
            )
            results = di.dev_announcements_service(message, target_telegram_username, configured_tool).execute()
            return __success(
                {
                    "summary": results,
                    "next_step": "Report these summary numbers back to the developer-user",
                },
            )
    except Exception as e:
        return __error(e)


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
            di = DI(db, author_user_id)
            configured_tool = di.tool_choice_resolver.require_tool(
                UserSupportService.TOOL_TYPE,
                UserSupportService.DEFAULT_TOOL,
            )
            service = di.user_support_service(
                user_request_details, author_github_username,
                include_telegram_username, include_full_name,
                request_type, configured_tool,
            )
            issue_url = service.execute()
            return __success(
                {
                    "github_issue_url": issue_url,
                    "next_step": "Report this resolution back to the partner",
                },
            )
    except Exception as e:
        return __error(e)


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
            di = DI(db, author_user_id, chat_id)
            settings_link = di.settings_controller.create_settings_link(
                raw_settings_type = raw_settings_type,
                target_chat_id = chat_id,
            )
            # let's send the settings link to the user's private chat, for security and privacy reasons
            if not di.invoker.telegram_chat_id:
                return __error("Author has no private chat with the bot; cannot send settings link")
            di.telegram_bot_sdk.send_button_link(di.invoker.telegram_chat_id, settings_link)
            if chat_id and chat_id == str(di.invoker.telegram_chat_id or 0):
                return __success(
                    {
                        "next_step": "Notify the user to click on the settings link above",
                    },
                )
            else:
                return __success(
                    {
                        "next_step": "Notify the user that the link was sent to their private chat",
                    },
                )

    except Exception as e:
        return __error(e)


@tool
def get_version() -> str:
    """
    Checks the current version of the bot (the latest version available to the users).
    """
    try:
        return __success(
            {
                "version": f"v{config.version}",
                "next_step": "Notify the user of the current (latest) version",
            },
        )
    except Exception as e:
        return __error(e)


# === Helper functions ===


def __success(content: dict[str, Any] | str) -> str:
    if isinstance(content, str):
        sprint(f"Tool call succeeded: {content}")
        return json.dumps({"result": "Success", "information": content})
    else:
        sprint(f"Tool call succeeded: {str(content)}")
        return json.dumps({"result": "Success", **content})


def __error(message: str | Exception) -> str:
    error_str: str
    if isinstance(message, str):
        sprint(f"Tool call failed: {message}")
        error_str = message
    else:
        sprint("Tool call failed", message)
        error_str = str(message)
    return json.dumps({"result": "Error", "information": error_str})


# === Tool Bindings ===


class LLMToolLibrary(BaseLLMToolBinder):

    def __init__(self):
        super().__init__(
            {
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
            },
        )
