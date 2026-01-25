# ruff: noqa: E501

import functools
import inspect
import json
from typing import Any, Callable

from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import tool

from di.di import DI
from features.chat.chat_agent import ChatAgent
from features.chat.chat_attachments_analyzer import ChatAttachmentsAnalyzer
from features.chat.chat_image_edit_service import ChatImageEditService
from features.chat.dev_announcements_service import DevAnnouncementsService
from features.images.smart_stable_diffusion_generator import SmartStableDiffusionGenerator
from features.integrations.integrations import add_messaging_frequency_warning, resolve_private_chat_id
from features.support.user_support_service import UserSupportService
from features.web_browsing.ai_web_search import AIWebSearch
from util import log
from util.config import config

TOOL_TRUNCATE_LENGTH = 8192  # to save some tokens

KEYWORD_ATTACHMENT_ANALYZE = "analyze"
KEYWORD_ATTACHMENT_IMAGE_EDIT = "image-edit"
ATTACHMENT_OPERATIONS = [KEYWORD_ATTACHMENT_ANALYZE, KEYWORD_ATTACHMENT_IMAGE_EDIT]


def process_attachments(
    di: DI,
    attachment_ids: str,
    operation: str = KEYWORD_ATTACHMENT_ANALYZE,
    context: str | None = None,
    aspect_ratio: str | None = None,
    size: str | None = None,
) -> str:
    """
    Processes the contents of the given attachments. Allowed operations are:
        - 'analyze' (default): Analyzes the image contents using vision, transcribes audio, searches documents
        - 'image-edit': Edits image attachments based on the context and user instructions

    Args:
        attachment_ids: [mandatory] A comma-separated list of verbatim, unique 📎 attachment IDs that need to be processed (located in each message); include any dashes, underscores or other symbols; these IDs are not to be cleaned or truncated
        operation: [mandatory] The action to perform on the attachments
        context: [optional] Additional task context or guidance, e.g. the user's message/question/caption, if available
        aspect_ratio: [optional] The desired image's aspect ratio for image editing. Valid options: 1:1, 2:3, 3:2, 3:4, 4:3, 16:9, 9:16, match_input_image. If not explicitly requested, don't send
        size: [optional] The desired image size/resolution for image editing. Valid options: 1K, 2K, 4K. If not explicitly requested, don't send
    """
    try:
        operation = operation.lower().strip()
        attachment_ids_list = attachment_ids.split(",")
        if operation == KEYWORD_ATTACHMENT_ANALYZE:
            # Analyze the attachments and convert contents to text descriptions
            analyzer = di.chat_attachments_analyzer(context, attachment_ids_list)
            result = analyzer.execute()
            if result == ChatAttachmentsAnalyzer.Result.failed:
                raise ValueError("Failed to resolve attachments")
            return json.dumps({"result": result.value, "attachments": analyzer.result})
        elif operation == KEYWORD_ATTACHMENT_IMAGE_EDIT:
            log.d(f"LLM requested to process {len(attachment_ids_list)} images in aspect ratio {aspect_ratio}, size {size}")
            # Generate images based on the provided context and attachments
            result, details = di.chat_image_edit_service(attachment_ids_list, context, aspect_ratio, size).execute()
            if result == ChatImageEditService.Result.failed:
                raise ValueError("Failed to edit the images! Details: " + str(details))
            return __success(
                {
                    "status": result.value,
                    "details": details,
                    "description": "Results were already delivered to the partner!",
                    "next_step": "You may deliver any errors to the partner (but no links or attachments)",
                },
            )
        else:
            raise ValueError(f"Unknown operation '{operation}'; try one of: [{', '.join(ATTACHMENT_OPERATIONS)}]")
    except Exception as e:
        return __error(e)


def generate_image(
    di: DI,
    prompt: str,
    aspect_ratio: str | None = None,
    size: str | None = None,
) -> str:
    """
    Generates (draws) a new image based on the given prompt using Generative AI.

    Args:
        prompt: [mandatory] The user's description or prompt for the generated image
        aspect_ratio: [optional] The desired image's aspect ratio. Valid options: 1:1, 2:3, 3:2, 3:4, 4:3, 16:9, 9:16. If not explicitly requested, don't send
        size: [optional] The desired image size/resolution. Valid options: 1K, 2K, 4K. If not explicitly requested, don't send
    """
    try:
        log.d(f"LLM requested to generate an image in aspect ratio {aspect_ratio}")
        copywriter_tool = di.tool_choice_resolver.require_tool(
            SmartStableDiffusionGenerator.COPYWRITER_TOOL_TYPE,
            SmartStableDiffusionGenerator.DEFAULT_COPYWRITER_TOOL,
        )
        image_gen_tool = di.tool_choice_resolver.require_tool(
            SmartStableDiffusionGenerator.IMAGE_GEN_TOOL_TYPE,
            SmartStableDiffusionGenerator.DEFAULT_IMAGE_GEN_TOOL,
        )
        generator = di.smart_stable_diffusion_generator(prompt, copywriter_tool, image_gen_tool, aspect_ratio, size)
        result = generator.execute()
        if result == SmartStableDiffusionGenerator.Result.failed:
            raise ValueError(f"Failed to generate the image! Reason: {str(generator.error)}")
        return __success({"next_step": "Confirm to partner that the image has been sent"})
    except Exception as e:
        return __error(e)


def fetch_web_content(di: DI, url: str) -> str:
    """
    Fetches the text content from the given web page URL.

    Args:
        url: [mandatory] A valid URL of the web page, starting with 'http://' or 'https://' provided in the text
    """
    try:
        fetcher = di.web_fetcher(url, auto_fetch_html = True)
        html = str(fetcher.html)
        text = di.html_content_cleaner(html).clean_up()
        result = text[:TOOL_TRUNCATE_LENGTH] + "..." if len(text) > TOOL_TRUNCATE_LENGTH else text
        return __success({"content": result})
    except Exception as e:
        return __error(e)


def get_exchange_rate(di: DI, base_currency: str, desired_currency: str, amount: str | None = None) -> str:
    """
    Fetches the exchange rate between two (crypto or fiat) currencies.

    Args:
        base_currency: [mandatory] The currency code of the base currency, e.g. 'USD' or 'BTC'
        desired_currency: [mandatory] The currency code of the desired currency, e.g. 'EUR' or 'ADA'
        amount: [optional] The amount of the base currency to convert; not sending this will assume value of 1.0
    """
    try:
        result = di.exchange_rate_fetcher.execute(base_currency, desired_currency, float(amount) if amount else 1.0)
        return __success({"exchange_rate": result})
    except Exception as e:
        return __error(e)


def set_up_currency_price_alert(
    di: DI,
    base_currency: str,
    desired_currency: str,
    threshold_percent: int,
) -> str:
    """
    Sets up a price alert at the given threshold for the given currency pair.

    Args:
        base_currency: [mandatory] The currency code of the base currency, e.g. 'USD' or 'BTC'
        desired_currency: [mandatory] The currency code of the desired currency, e.g. 'EUR' or 'ADA'
        threshold_percent: [mandatory] The trigger threshold, in percent [0-100], that triggers the price alert
    """
    try:
        service = di.currency_alert_service(di.invoker_chat_id)
        alert = service.create_alert(base_currency, desired_currency, threshold_percent)
        response_data: dict[str, Any] = {"created_alert_data": alert.model_dump(mode = "json")}
        add_messaging_frequency_warning(response_data, di.invoker_chat_type)
        return __success(response_data)
    except Exception as e:
        return __error(e)


def remove_currency_price_alerts(di: DI, base_currency: str, desired_currency: str) -> str:
    """
    Deletes the oldest price alert for the given currency pair.

    Args:
        base_currency: [mandatory] The currency code of the base currency, e.g. 'USD' or 'BTC'
        desired_currency: [mandatory] The currency code of the desired currency, e.g. 'EUR' or 'ADA'
    """
    try:
        service = di.currency_alert_service(di.invoker_chat_id)
        alert = service.delete_alert(base_currency, desired_currency)
        deleted_alert_data = alert.model_dump(mode = "json") if alert else None
        return __success({"deleted_alert_data": deleted_alert_data})
    except Exception as e:
        return __error(e)


def list_currency_price_alerts(di: DI) -> str:
    """
    Lists all price alerts.

    Args:
        None.
    """
    try:
        service = di.currency_alert_service(di.invoker_chat_id)
        alerts = service.get_active_alerts()
        return __success({"alerts": [alert.model_dump(mode = "json") for alert in alerts]})
    except Exception as e:
        return __error(e)


def ai_web_search(di: DI, search_query: str) -> str:
    """
    Searches the web for the given query, and responds using AI. To be used any time there's missing information or upon user request.

    Args:
        search_query: [mandatory] The user's search query, in English
    """
    try:
        configured_tool = di.tool_choice_resolver.require_tool(AIWebSearch.TOOL_TYPE, AIWebSearch.DEFAULT_TOOL)
        search = di.ai_web_search(search_query, configured_tool)
        result = search.execute()
        if not result.content:
            raise ValueError("Answer not received")
        return __success({"content": result.content})
    except Exception as e:
        return __error(e)


def announce_maintenance_or_news(di: DI, raw_announcement: str) -> str:
    """
    [Developers-only] Announces a maintenance or news message from developers to all chats.

    Args:
        raw_announcement: [mandatory] The raw announcement message to send to all chats
    """
    try:
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


def deliver_message(di: DI, message: str, target_handle: str) -> str:
    """
    [Developers-only] Delivers a personalized message from developers to a specific user.

    Args:
        message: [mandatory] The message to deliver to the target user
        target_handle: [mandatory] The full social handle (e.g. username, phone, email) of the target user to send the message to, without '@' or '+'
    """
    try:
        configured_tool = di.tool_choice_resolver.require_tool(
            DevAnnouncementsService.TOOL_TYPE,
            DevAnnouncementsService.DEFAULT_TOOL,
        )
        results = di.dev_announcements_service(message, target_handle, configured_tool).execute()
        return __success(
            {
                "summary": results,
                "next_step": "Report these summary numbers back to the developer-user",
            },
        )
    except Exception as e:
        return __error(e)


def request_feature_bug_or_support(
    di: DI,
    user_request_details: str,
    request_type: str | None = None,
    include_full_name: bool = False,
    include_platform_handle: bool = False,
    author_github_username: str | None = None,
) -> str:
    """
    Allows the user to request a feature, report a bug, or ask for support. As a result, a GitHub issue is created.
    Conversing with the user helps gather more details (based on this function's arguments).
    This function must be explicitly called once the user is ready to submit the request.

    Args:
        user_request_details: [mandatory] The raw text of the user's request, bug report, or support question
        include_full_name: [mandatory] Whether to include the user's full name in the GitHub issue
        include_platform_handle: [mandatory] Whether to include the current platform's handle in the GitHub issue (username, phone, email)
        request_type: [optional] The type of the request: [ 'feature', 'bug', 'request' ]
        author_github_username: [optional] The GitHub username of the author, if available and shared
    """
    try:
        configured_tool = di.tool_choice_resolver.require_tool(
            UserSupportService.TOOL_TYPE,
            UserSupportService.DEFAULT_TOOL,
        )
        service = di.user_support_service(
            user_request_details, author_github_username,
            include_platform_handle, include_full_name,
            request_type, configured_tool,
        )
        issue_url = service.execute()
        return __success(
            {
                "github_issue_url": issue_url,
                "next_step": "Report this link back to the partner",
            },
        )
    except Exception as e:
        return __error(e)


def configure_settings(
    di: DI,
    raw_settings_type: str,
) -> str:
    """
    Launches the configuration screen. Configurations allow various profile settings, payments, API tokens/keys,
    current chat's settings, language, response rate, release notifications, model options, etc. Profile settings also
    serve as the initial setup for the agent (bot). In private chats, user settings are the default. The user will
    probably not know which settings they need, so they must either be chosen for, or asked.

    Args:
        raw_settings_type: [mandatory] The type of settings the user wants: [ 'user', 'chat' ]
    """
    try:
        settings_link = di.settings_controller.create_settings_link(raw_settings_type).settings_link
        platform_private_chat_id = resolve_private_chat_id(di.invoker, di.require_invoker_chat_type())
        if not platform_private_chat_id:
            return __error("Author has no private chat with the agent; cannot send settings link")
        di.platform_bot_sdk().send_button_link(platform_private_chat_id, settings_link)
        if di.require_invoker_chat().is_private:
            return __success({"next_step": "Notify the user to click on the settings link above"})
        else:
            return __success({"next_step": "Notify the user that the link was sent to their private chat"})
    except Exception as e:
        return __error(e)


def read_help_and_features(
    di: DI,
) -> str:
    """
    Launches the help screen. This allows the user to understand more about the service, how to use it,
    look for help or FAQ, as well as check the details of the many features available in the service.
    This does not allow the user to request support or report issues - use another tool for that.

    Args:
        None.
    """
    try:
        help_link = di.settings_controller.create_help_link()
        platform_private_chat_id = resolve_private_chat_id(di.invoker, di.require_invoker_chat_type())
        if not platform_private_chat_id:
            return __error("Author has no private chat with the agent; cannot send settings link")
        di.platform_bot_sdk().send_button_link(platform_private_chat_id, help_link)
        return __success({"next_step": "Notify the user that the link was sent to their private chat"})
    except Exception as e:
        return __error(e)


def get_version(di: DI) -> str:
    """
    Checks the current version of the agent (the latest version available to the users).
    """
    try:
        log.t(f"Getting version for chat '{di.invoker_chat_id}'")
        tool, _, _ = di.tool_choice_resolver.require_tool(ChatAgent.TOOL_TYPE, ChatAgent.DEFAULT_TOOL)
        return __success(
            {
                "service_version": f"v{config.version}",
                "chat_agent_version": f"{tool.name} from {tool.provider.name}",
                "next_step": "Notify the user of the current (latest) version",
            },
        )
    except Exception as e:
        return __error(e)


def connect_profiles(di: DI, connect_key: str) -> str:
    """
    Connects the current user profile with another profile using a connect key. This allows users to
    (for example) merge their Telegram and WhatsApp accounts into a single unified profile, or merge
    any other two profiles together — provided they have the other profile's connect key. The connect
    key is usually a 12-character code in the format XXXX-XXXX-XXXX that can be obtained from the
    settings page of any profile. The user must provide this key to connect their profiles together.

    Args:
        connect_key: [mandatory] The connect key from the other profile that you want to connect with
    """
    try:
        result, message = di.profile_connect_service.connect_profiles(di.invoker, connect_key)
        if result == di.profile_connect_service.Result.failure:
            raise ValueError(message)
        return __success({"status": "success", "message": message})
    except Exception as e:
        return __error(e)


# === Helper functions ===


def __success(content: dict[str, Any] | str) -> str:
    if isinstance(content, str):
        log.t(f"Tool call succeeded: {content}")
        return json.dumps({"result": "Success", "information": content})
    else:
        log.t(f"Tool call succeeded: {str(content)}")
        return json.dumps({"result": "Success", **content})


def __error(message: str | Exception) -> str:
    error_str: str
    if isinstance(message, str):
        error_str = log.e(f"Tool call failed: {message}")
    else:
        error_str = log.e("Tool call failed", message)
    return json.dumps({"result": "Error", "information": error_str})


# === Tool Bindings ===


ALL_LLM_TOOLS: dict[str, Callable[..., str]] = {
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
    "read_help_and_features": read_help_and_features,
    "get_version": get_version,
    "connect_profiles": connect_profiles,
}


class LLMToolLibrary:

    _di: DI
    _impls: dict[str, Callable[..., str]]
    _wrapped_tools: dict[str, Any]

    def __init__(self, di: DI):
        self._di = di
        self._impls = {}
        self._wrapped_tools = {}
        for name, func in ALL_LLM_TOOLS.items():
            wrapped = self._wrap_with_di(func)
            self._impls[name] = wrapped
            self._wrapped_tools[name] = tool(wrapped)

    def _wrap_with_di(self, func: Callable[..., str]) -> Callable[..., str]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(self._di, *args, **kwargs)

        # Clean the signature so DI is hidden from the LLM
        orig_sig = inspect.signature(func)
        params = list(orig_sig.parameters.values())[1:]
        cleaned_sig = orig_sig.replace(parameters = params)
        try:
            wrapper.__signature__ = cleaned_sig  # type: ignore[attr-defined]
        except Exception:
            pass
        return wrapper

    def bind_tools(self, llm_base: BaseChatModel) -> Runnable[LanguageModelInput, BaseMessage]:
        return llm_base.bind_tools(list(self._wrapped_tools.values()))

    def invoke(self, tool_name: str, args: object) -> str | None:
        impl = self._impls.get(tool_name)
        if impl is None:
            log.w(f"Tool {tool_name} not found for invocation")
            return None
        if isinstance(args, dict):
            return impl(**args)
        return impl(args)

    @property
    def tool_names(self) -> list[str]:
        return list(self._wrapped_tools.keys())
