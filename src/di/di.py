from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

# noinspection PyUnusedImports
from langchain_core.messages import BaseMessage
from sqlalchemy.orm import Session

from db.model.chat_config import ChatConfigDB
from db.schema.chat_config import ChatConfig
from db.schema.user import User

if TYPE_CHECKING:

    from google.genai import Client as GoogleSDKClient
    from openai import OpenAI
    from replicate.client import Client as ReplicateSDKClient

    from api.authorization_service import AuthorizationService
    from api.gumroad_controller import GumroadController
    from api.profile_connect_controller import ProfileConnectController
    from api.settings_controller import SettingsController
    from api.sponsorships_controller import SponsorshipsController
    from api.usage_controller import UsageController
    from db.crud.chat_config import ChatConfigCRUD
    from db.crud.chat_message import ChatMessageCRUD
    from db.crud.chat_message_attachment import ChatMessageAttachmentCRUD
    from db.crud.price_alert import PriceAlertCRUD
    from db.crud.sponsorship import SponsorshipCRUD
    from db.crud.tools_cache import ToolsCacheCRUD
    from db.crud.user import UserCRUD
    from features.accounting.decorators.chat_model_usage_tracking_decorator import ChatModelUsageTrackingDecorator
    from features.accounting.decorators.google_ai_usage_tracking_decorator import GoogleAIUsageTrackingDecorator
    from features.accounting.decorators.http_usage_tracking_decorator import HTTPUsageTrackingDecorator
    from features.accounting.decorators.openai_usage_tracking_decorator import OpenAIUsageTrackingDecorator
    from features.accounting.decorators.replicate_usage_tracking_decorator import ReplicateUsageTrackingDecorator
    from features.accounting.decorators.web_fetcher_usage_tracking_decorator import WebFetcherUsageTrackingDecorator
    from features.accounting.repo.usage_record_repo import UsageRecordRepository
    from features.accounting.service.usage_tracking_service import UsageTrackingService
    from features.announcements.release_summary_service import ReleaseSummaryService
    from features.announcements.sys_announcements_service import SysAnnouncementsService
    from features.audio.audio_transcriber import AudioTranscriber
    from features.chat.chat_agent import ChatAgent
    from features.chat.chat_attachments_analyzer import ChatAttachmentsAnalyzer
    from features.chat.chat_image_edit_service import ChatImageEditService
    from features.chat.chat_progress_notifier import ChatProgressNotifier
    from features.chat.command_processor import CommandProcessor
    from features.chat.currency_alert_service import CurrencyAlertService
    from features.chat.dev_announcements_service import DevAnnouncementsService
    from features.chat.llm_tools.llm_tool_library import LLMToolLibrary
    from features.chat.telegram.domain_langchain_mapper import DomainLangchainMapper
    from features.chat.telegram.sdk.telegram_bot_api import TelegramBotAPI
    from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
    from features.chat.telegram.telegram_data_resolver import TelegramDataResolver
    from features.chat.telegram.telegram_domain_mapper import TelegramDomainMapper
    from features.chat.whatsapp.sdk.whatsapp_bot_api import WhatsAppBotAPI
    from features.chat.whatsapp.sdk.whatsapp_bot_sdk import WhatsAppBotSDK
    from features.chat.whatsapp.whatsapp_data_resolver import WhatsAppDataResolver
    from features.chat.whatsapp.whatsapp_domain_mapper import WhatsAppDomainMapper
    from features.connect.profile_connect_service import ProfileConnectService
    from features.currencies.exchange_rate_fetcher import ExchangeRateFetcher
    from features.documents.document_search import DocumentSearch
    from features.documents.langchain_embeddings_adapter import LangChainEmbeddingsAdapter
    from features.external_tools.access_token_resolver import AccessTokenResolver
    from features.external_tools.tool_choice_resolver import ConfiguredTool, ToolChoiceResolver
    from features.images.computer_vision_analyzer import ComputerVisionAnalyzer
    from features.images.image_editor import ImageEditor
    from features.images.image_uploader import ImageUploader
    from features.images.simple_stable_diffusion_generator import SimpleStableDiffusionGenerator
    from features.images.smart_stable_diffusion_generator import SmartStableDiffusionGenerator
    from features.integrations.platform_bot_sdk import PlatformBotSDK
    from features.sponsorships.sponsorship_service import SponsorshipService
    from features.support.user_support_service import UserSupportService
    from features.web_browsing.ai_web_search import AIWebSearch
    from features.web_browsing.html_content_cleaner import HTMLContentCleaner
    from features.web_browsing.twitter_status_fetcher import TwitterStatusFetcher
    from features.web_browsing.url_shortener import UrlShortener
    from features.web_browsing.web_fetcher import WebFetcher
    from util.translations_cache import TranslationsCache


class ConstructorDependencyNotMetError(Exception):
    pass


class DI:

    # Dynamic dependencies
    _db: Session | None
    _invoker_id: str | None
    _invoker_chat_id: str | None
    _invoker: User | None
    _invoker_chat: ChatConfig | None
    # SDKs
    _telegram_bot_api: "TelegramBotAPI | None"
    _whatsapp_bot_api: "WhatsAppBotAPI | None"
    _telegram_bot_sdk: "TelegramBotSDK | None"
    _whatsapp_bot_sdk: "WhatsAppBotSDK | None"
    # Repositories
    _user_crud: "UserCRUD | None"
    _chat_config_crud: "ChatConfigCRUD | None"
    _chat_message_crud: "ChatMessageCRUD | None"
    _chat_message_attachment_crud: "ChatMessageAttachmentCRUD | None"
    _sponsorship_crud: "SponsorshipCRUD | None"
    _tools_cache_crud: "ToolsCacheCRUD | None"
    _price_alert_crud: "PriceAlertCRUD | None"
    _usage_record_repo: "UsageRecordRepository | None"
    # Services
    _sponsorship_service: "SponsorshipService | None"
    _profile_connect_service: "ProfileConnectService | None"
    _authorization_service: "AuthorizationService | None"
    _usage_tracking_service: "UsageTrackingService | None"
    # Controllers
    _settings_controller: "SettingsController | None"
    _sponsorships_controller: "SponsorshipsController | None"
    _usage_controller: "UsageController | None"
    _profile_connect_controller: "ProfileConnectController | None"
    _gumroad_controller: "GumroadController | None"
    # Internal tools
    _access_token_resolver: "AccessTokenResolver | None"
    _tool_choice_resolver: "ToolChoiceResolver | None"
    _domain_langchain_mapper: "DomainLangchainMapper | None"
    _telegram_domain_mapper: "TelegramDomainMapper | None"
    _whatsapp_domain_mapper: "WhatsAppDomainMapper | None"
    _telegram_data_resolver: "TelegramDataResolver | None"
    _whatsapp_data_resolver: "WhatsAppDataResolver | None"
    # Features & Dynamic Instances
    _llm_tool_library: "LLMToolLibrary | None"
    _command_processor: "CommandProcessor | None"
    _exchange_rate_fetcher: "ExchangeRateFetcher | None"

    def __init__(
        self,
        db: Session | None = None,
        invoker_id: str | None = None,
        invoker_chat_id: str | None = None,
    ):
        # Dynamic dependencies
        self._db = db
        self._invoker_id = invoker_id
        self._invoker_chat_id = invoker_chat_id
        self._invoker = None
        self._invoker_chat = None
        # SDKs
        self._telegram_bot_api = None
        self._whatsapp_bot_api = None
        self._telegram_bot_sdk = None
        self._whatsapp_bot_sdk = None
        # Repositories
        self._user_crud = None
        self._chat_config_crud = None
        self._chat_message_crud = None
        self._chat_message_attachment_crud = None
        self._sponsorship_crud = None
        self._tools_cache_crud = None
        self._price_alert_crud = None
        self._usage_record_repo = None
        # Services
        self._sponsorship_service = None
        self._profile_connect_service = None
        self._authorization_service = None
        self._usage_tracking_service = None
        # Controllers
        self._settings_controller = None
        self._sponsorships_controller = None
        self._usage_controller = None
        self._profile_connect_controller = None
        self._gumroad_controller = None
        # Internal tools
        self._access_token_resolver = None
        self._tool_choice_resolver = None
        self._domain_langchain_mapper = None
        self._telegram_domain_mapper = None
        self._whatsapp_domain_mapper = None
        self._telegram_data_resolver = None
        self._whatsapp_data_resolver = None
        # Features & Dynamic Instances
        self._llm_tool_library = None
        self._command_processor = None
        self._exchange_rate_fetcher = None

    # === Cloning ===

    def clone(
        self,
        db: Session | None = None,
        invoker_id: str | None = None,
        invoker_chat_id: str | None = None,
    ) -> "DI":
        return DI(
            db or self._db,
            invoker_id or self._invoker_id,
            invoker_chat_id or self._invoker_chat_id,
        )

    # === Dynamic dependencies ===

    @property
    def db(self) -> Session:
        if self._db is None:
            raise ConstructorDependencyNotMetError("Database session not provided")
        return self._db

    @property
    def invoker_id(self) -> str:
        if self._invoker_id is None:
            raise ConstructorDependencyNotMetError("Invoker ID not provided")
        return self._invoker_id

    @property
    def invoker_chat_id(self) -> str:
        if self._invoker_chat_id is None:
            raise ConstructorDependencyNotMetError("Invoker chat ID not provided")
        return self._invoker_chat_id

    @property
    def invoker(self) -> User:
        if self._invoker is None:
            try:
                self._invoker = self.authorization_service.validate_user(self.invoker_id)
            except Exception as e:
                raise ConstructorDependencyNotMetError(f"Invoker validation failed: {e}")
        return self._invoker

    @property
    def invoker_chat(self) -> ChatConfig | None:
        if self._invoker_chat_id is not None and self._invoker_chat is None:
            try:
                self._invoker_chat = self.authorization_service.validate_chat(self.invoker_chat_id)
            except Exception as e:
                raise ConstructorDependencyNotMetError(f"Invoker chat validation failed: {e}")
        return self._invoker_chat

    @property
    def invoker_chat_type(self) -> ChatConfigDB.ChatType | None:
        if self.invoker_chat is not None:
            return self.invoker_chat.chat_type
        return None

    def require_invoker_chat(self) -> ChatConfig:
        if self.invoker_chat is None:
            raise ConstructorDependencyNotMetError("Chat context is required for this operation")
        return self.invoker_chat

    def require_invoker_chat_type(self) -> ChatConfigDB.ChatType:
        if self.invoker_chat_type is None:
            raise ConstructorDependencyNotMetError("Chat type is required for this operation")
        return self.invoker_chat_type

    # === Dynamic injections ===

    def inject_invoker_id(self, invoker_id: str | None):
        self._invoker_id = invoker_id
        if self._invoker and self._invoker.id.hex != invoker_id:
            self._invoker = None

    def inject_invoker(self, invoker: User | None):
        if not invoker:
            self._invoker = None
            self._invoker_id = None
            return
        self._invoker = invoker
        if not self._invoker_id or self._invoker_id != invoker.id:
            self._invoker_id = invoker.id.hex

    def inject_invoker_chat_id(self, invoker_chat_id: str | None):
        self._invoker_chat_id = invoker_chat_id
        if self._invoker_chat and self._invoker_chat.chat_id.hex != invoker_chat_id:
            self._invoker_chat = None

    def inject_invoker_chat(self, invoker_chat: ChatConfig | None):
        if not invoker_chat:
            self._invoker_chat = None
            self._invoker_chat_id = None
            return
        self._invoker_chat = invoker_chat
        if not self._invoker_chat_id or self._invoker_chat_id != invoker_chat.chat_id.hex:
            self._invoker_chat_id = invoker_chat.chat_id.hex

    # === SDKs ===

    @property
    def telegram_bot_api(self) -> "TelegramBotAPI":
        if self._telegram_bot_api is None:
            from features.chat.telegram.sdk.telegram_bot_api import TelegramBotAPI
            self._telegram_bot_api = TelegramBotAPI()
        return self._telegram_bot_api

    @property
    def whatsapp_bot_api(self) -> "WhatsAppBotAPI":
        if self._whatsapp_bot_api is None:
            from features.chat.whatsapp.sdk.whatsapp_bot_api import WhatsAppBotAPI
            self._whatsapp_bot_api = WhatsAppBotAPI()
        return self._whatsapp_bot_api

    @property
    def telegram_bot_sdk(self) -> "TelegramBotSDK":
        if self._telegram_bot_sdk is None:
            from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
            self._telegram_bot_sdk = TelegramBotSDK(self)
        return self._telegram_bot_sdk

    @property
    def whatsapp_bot_sdk(self) -> "WhatsAppBotSDK":
        if self._whatsapp_bot_sdk is None:
            from features.chat.whatsapp.sdk.whatsapp_bot_sdk import WhatsAppBotSDK
            self._whatsapp_bot_sdk = WhatsAppBotSDK(self)
        return self._whatsapp_bot_sdk

    # === Repositories ===

    @property
    def user_crud(self) -> "UserCRUD":
        if self._user_crud is None:
            from db.crud.user import UserCRUD
            self._user_crud = UserCRUD(self.db)
        return self._user_crud

    @property
    def chat_config_crud(self) -> "ChatConfigCRUD":
        if self._chat_config_crud is None:
            from db.crud.chat_config import ChatConfigCRUD
            self._chat_config_crud = ChatConfigCRUD(self.db)
        return self._chat_config_crud

    @property
    def chat_message_crud(self) -> "ChatMessageCRUD":
        if self._chat_message_crud is None:
            from db.crud.chat_message import ChatMessageCRUD
            self._chat_message_crud = ChatMessageCRUD(self.db)
        return self._chat_message_crud

    @property
    def chat_message_attachment_crud(self) -> "ChatMessageAttachmentCRUD":
        if self._chat_message_attachment_crud is None:
            from db.crud.chat_message_attachment import ChatMessageAttachmentCRUD
            self._chat_message_attachment_crud = ChatMessageAttachmentCRUD(self.db)
        return self._chat_message_attachment_crud

    @property
    def sponsorship_crud(self) -> "SponsorshipCRUD":
        if self._sponsorship_crud is None:
            from db.crud.sponsorship import SponsorshipCRUD
            self._sponsorship_crud = SponsorshipCRUD(self.db)
        return self._sponsorship_crud

    @property
    def tools_cache_crud(self) -> "ToolsCacheCRUD":
        if self._tools_cache_crud is None:
            from db.crud.tools_cache import ToolsCacheCRUD
            self._tools_cache_crud = ToolsCacheCRUD(self.db)
        return self._tools_cache_crud

    @property
    def price_alert_crud(self) -> "PriceAlertCRUD":
        if self._price_alert_crud is None:
            from db.crud.price_alert import PriceAlertCRUD
            self._price_alert_crud = PriceAlertCRUD(self.db)
        return self._price_alert_crud

    @property
    def usage_record_repo(self) -> "UsageRecordRepository":
        if self._usage_record_repo is None:
            from features.accounting.repo.usage_record_repo import UsageRecordRepository
            self._usage_record_repo = UsageRecordRepository(self.db)
        return self._usage_record_repo

    # === Services ===

    @property
    def sponsorship_service(self) -> "SponsorshipService":
        if self._sponsorship_service is None:
            from features.sponsorships.sponsorship_service import SponsorshipService
            self._sponsorship_service = SponsorshipService(self)
        return self._sponsorship_service

    @property
    def authorization_service(self) -> "AuthorizationService":
        if self._authorization_service is None:
            from api.authorization_service import AuthorizationService
            self._authorization_service = AuthorizationService(self)
        return self._authorization_service

    @property
    def usage_tracking_service(self) -> "UsageTrackingService":
        if self._usage_tracking_service is None:
            from features.accounting.service.usage_tracking_service import UsageTrackingService
            self._usage_tracking_service = UsageTrackingService(self)
        return self._usage_tracking_service

    @property
    def profile_connect_service(self) -> "ProfileConnectService":
        if self._profile_connect_service is None:
            from features.connect.profile_connect_service import ProfileConnectService
            self._profile_connect_service = ProfileConnectService(self)
        return self._profile_connect_service

    # === Controllers ===

    @property
    def settings_controller(self) -> "SettingsController":
        if self._settings_controller is None:
            from api.settings_controller import SettingsController
            self._settings_controller = SettingsController(self)
        return self._settings_controller

    @property
    def sponsorships_controller(self) -> "SponsorshipsController":
        if self._sponsorships_controller is None:
            from api.sponsorships_controller import SponsorshipsController
            self._sponsorships_controller = SponsorshipsController(self)
        return self._sponsorships_controller

    @property
    def usage_controller(self) -> "UsageController":
        if self._usage_controller is None:
            from api.usage_controller import UsageController
            self._usage_controller = UsageController(self)
        return self._usage_controller

    @property
    def profile_connect_controller(self) -> "ProfileConnectController":
        if self._profile_connect_controller is None:
            from api.profile_connect_controller import ProfileConnectController
            self._profile_connect_controller = ProfileConnectController(self)
        return self._profile_connect_controller

    @property
    def gumroad_controller(self) -> "GumroadController":
        if self._gumroad_controller is None:
            from api.gumroad_controller import GumroadController
            self._gumroad_controller = GumroadController(self)
        return self._gumroad_controller

    # === Internal tools ===

    @property
    def access_token_resolver(self) -> "AccessTokenResolver":
        if self._access_token_resolver is None:
            from features.external_tools.access_token_resolver import AccessTokenResolver
            self._access_token_resolver = AccessTokenResolver(self)
        return self._access_token_resolver

    @property
    def tool_choice_resolver(self) -> "ToolChoiceResolver":
        if self._tool_choice_resolver is None:
            from features.external_tools.tool_choice_resolver import ToolChoiceResolver
            self._tool_choice_resolver = ToolChoiceResolver(self)
        return self._tool_choice_resolver

    @property
    def translations_cache(self) -> "TranslationsCache":
        from util.translations_cache import TranslationsCache
        return TranslationsCache()

    @property
    def domain_langchain_mapper(self) -> "DomainLangchainMapper":
        if self._domain_langchain_mapper is None:
            from features.chat.telegram.domain_langchain_mapper import DomainLangchainMapper
            self._domain_langchain_mapper = DomainLangchainMapper()
        return self._domain_langchain_mapper

    @property
    def telegram_domain_mapper(self) -> "TelegramDomainMapper":
        if self._telegram_domain_mapper is None:
            from features.chat.telegram.telegram_domain_mapper import TelegramDomainMapper
            self._telegram_domain_mapper = TelegramDomainMapper()
        return self._telegram_domain_mapper

    @property
    def whatsapp_domain_mapper(self) -> "WhatsAppDomainMapper":
        if self._whatsapp_domain_mapper is None:
            from features.chat.whatsapp.whatsapp_domain_mapper import WhatsAppDomainMapper
            self._whatsapp_domain_mapper = WhatsAppDomainMapper()
        return self._whatsapp_domain_mapper

    @property
    def telegram_data_resolver(self) -> "TelegramDataResolver":
        if self._telegram_data_resolver is None:
            from features.chat.telegram.telegram_data_resolver import TelegramDataResolver
            self._telegram_data_resolver = TelegramDataResolver(self)
        return self._telegram_data_resolver

    @property
    def whatsapp_data_resolver(self) -> "WhatsAppDataResolver":
        if self._whatsapp_data_resolver is None:
            from features.chat.whatsapp.whatsapp_data_resolver import WhatsAppDataResolver
            self._whatsapp_data_resolver = WhatsAppDataResolver(self)
        return self._whatsapp_data_resolver

    # === Features & Dynamic Instances ===

    def chat_langchain_model(self, configured_tool: ConfiguredTool) -> "ChatModelUsageTrackingDecorator":
        from features.accounting.decorators.chat_model_usage_tracking_decorator import ChatModelUsageTrackingDecorator
        from features.llm import langchain_creator

        base_model = langchain_creator.create(configured_tool)
        return ChatModelUsageTrackingDecorator(
            base_model,
            self.usage_tracking_service,
            configured_tool.definition,
            configured_tool.purpose,
        )

    def base_replicate_client(self, api_token: str, timeout_s: float | None = None) -> "ReplicateSDKClient":
        from httpx import Timeout
        from replicate.client import Client as ReplicateSDKClient

        return ReplicateSDKClient(
            api_token = api_token,
            timeout = Timeout(timeout_s) if timeout_s is not None else None,
        )

    def replicate_client(
        self,
        configured_tool: ConfiguredTool,
        timeout_s: float | None = None,
        output_image_sizes: list[str] | None = None,
        input_image_sizes: list[str] | None = None,
    ) -> "ReplicateUsageTrackingDecorator":
        from features.accounting.decorators.replicate_usage_tracking_decorator import ReplicateUsageTrackingDecorator

        base_client = self.base_replicate_client(configured_tool.token.get_secret_value(), timeout_s)
        return ReplicateUsageTrackingDecorator(
            base_client,
            self.usage_tracking_service,
            configured_tool.definition,
            configured_tool.purpose,
            output_image_sizes,
            input_image_sizes,
        )

    def base_google_ai_client(
        self,
        api_key: str,
        timeout_s: float | None = None,
    ) -> "GoogleSDKClient":
        from google.genai import Client as GoogleSDKClient
        from google.genai.types import HttpOptions

        http_options: HttpOptions | None = None
        if timeout_s is not None:
            http_options = HttpOptions(timeout = int(timeout_s * 1000))
        return GoogleSDKClient(api_key = api_key, http_options = http_options)

    def google_ai_client(
        self,
        configured_tool: ConfiguredTool,
        timeout_s: float | None = None,
        output_image_sizes: list[str] | None = None,
        input_image_sizes: list[str] | None = None,
    ) -> "GoogleAIUsageTrackingDecorator":
        from features.accounting.decorators.google_ai_usage_tracking_decorator import GoogleAIUsageTrackingDecorator

        base_client = self.base_google_ai_client(configured_tool.token.get_secret_value(), timeout_s)
        return GoogleAIUsageTrackingDecorator(
            base_client,
            self.usage_tracking_service,
            configured_tool.definition,
            configured_tool.purpose,
            output_image_sizes,
            input_image_sizes,
        )

    def base_open_ai_client(
        self,
        configured_tool: ConfiguredTool,
        timeout_s: float | None = None,
    ) -> "OpenAI":
        from openai import OpenAI

        return OpenAI(api_key = configured_tool.token.get_secret_value(), timeout = timeout_s)

    def open_ai_client(
        self,
        configured_tool: ConfiguredTool,
        timeout_s: float | None = None,
    ) -> "OpenAIUsageTrackingDecorator":
        from features.accounting.decorators.openai_usage_tracking_decorator import OpenAIUsageTrackingDecorator

        base_client = self.base_open_ai_client(configured_tool, timeout_s)
        return OpenAIUsageTrackingDecorator(
            base_client,
            self.usage_tracking_service,
            configured_tool.definition,
            configured_tool.purpose,
        )

    def openai_embeddings(self, configured_tool: ConfiguredTool) -> "LangChainEmbeddingsAdapter":
        from features.documents.langchain_embeddings_adapter import LangChainEmbeddingsAdapter

        client = self.open_ai_client(configured_tool)
        return LangChainEmbeddingsAdapter(client, configured_tool.definition.id)

    def tracked_http_get(self, configured_tool: ConfiguredTool) -> "HTTPUsageTrackingDecorator":
        from features.accounting.decorators.http_usage_tracking_decorator import HTTPUsageTrackingDecorator

        return HTTPUsageTrackingDecorator(
            self.usage_tracking_service,
            configured_tool.definition,
            configured_tool.purpose,
        )

    @property
    def llm_tool_library(self) -> "LLMToolLibrary":
        if self._llm_tool_library is None:
            from features.chat.llm_tools.llm_tool_library import LLMToolLibrary
            self._llm_tool_library = LLMToolLibrary(self)
        return self._llm_tool_library

    def platform_bot_sdk(self) -> "PlatformBotSDK":
        from features.integrations.platform_bot_sdk import PlatformBotSDK
        return PlatformBotSDK(di = self)

    def chat_progress_notifier(
        self,
        message_id: str,
        auto_start: bool = False,
    ) -> "ChatProgressNotifier":
        from features.chat.chat_progress_notifier import ChatProgressNotifier
        return ChatProgressNotifier(message_id, self, auto_start)

    @property
    def command_processor(self) -> "CommandProcessor":
        if self._command_processor is None:
            from features.chat.command_processor import CommandProcessor
            self._command_processor = CommandProcessor(self)
        return self._command_processor

    def chat_agent(
        self,
        messages: list[BaseMessage],
        raw_last_message: str,
        last_message_id: str,
        attachment_ids: list[str],
        configured_tool: ConfiguredTool | None,
    ) -> "ChatAgent":
        from features.chat.chat_agent import ChatAgent
        return ChatAgent(messages, raw_last_message, last_message_id, attachment_ids, configured_tool, self)

    def web_fetcher(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        cache_ttl_html: timedelta | None = None,
        cache_ttl_json: timedelta | None = None,
        auto_fetch_html: bool = False,
        auto_fetch_json: bool = False,
    ) -> "WebFetcher":
        from features.web_browsing.web_fetcher import WebFetcher
        return WebFetcher(
            url, self,
            headers, params,
            cache_ttl_html, cache_ttl_json,
            auto_fetch_html, auto_fetch_json,
        )

    def tracked_web_fetcher(
        self,
        configured_tool: ConfiguredTool,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        cache_ttl_html: timedelta | None = None,
        cache_ttl_json: timedelta | None = None,
        auto_fetch_html: bool = False,
        auto_fetch_json: bool = False,
    ) -> "WebFetcherUsageTrackingDecorator":
        from features.accounting.decorators.web_fetcher_usage_tracking_decorator import WebFetcherUsageTrackingDecorator

        base_fetcher = self.web_fetcher(
            url, headers, params,
            cache_ttl_html, cache_ttl_json,
            auto_fetch_html, auto_fetch_json,
        )
        return WebFetcherUsageTrackingDecorator(
            base_fetcher,
            self.usage_tracking_service,
            configured_tool.definition,
            configured_tool.purpose,
        )

    def html_content_cleaner(self, raw_html: str) -> "HTMLContentCleaner":
        from features.web_browsing.html_content_cleaner import HTMLContentCleaner
        return HTMLContentCleaner(raw_html, self)

    def twitter_status_fetcher(
        self,
        tweet_id: str,
        twitter_api_tool: ConfiguredTool,
        vision_tool: ConfiguredTool,
        twitter_enterprise_tool: ConfiguredTool,
    ) -> "TwitterStatusFetcher":
        from features.web_browsing.twitter_status_fetcher import TwitterStatusFetcher
        return TwitterStatusFetcher(tweet_id, twitter_api_tool, vision_tool, twitter_enterprise_tool, self)

    def url_shortener(
        self,
        long_url: str,
        custom_slug: str | None = None,
        valid_until: datetime | None = None,
        max_visits: int | None = None,
    ) -> "UrlShortener":
        from features.web_browsing.url_shortener import UrlShortener
        return UrlShortener(long_url, custom_slug, valid_until, max_visits)

    @property
    def exchange_rate_fetcher(self) -> "ExchangeRateFetcher":
        if self._exchange_rate_fetcher is None:
            from features.currencies.exchange_rate_fetcher import ExchangeRateFetcher
            self._exchange_rate_fetcher = ExchangeRateFetcher(self)
        return self._exchange_rate_fetcher

    # noinspection PyMethodMayBeStatic
    def ai_web_search(self, search_query: str, configured_tool: ConfiguredTool) -> "AIWebSearch":
        from features.web_browsing.ai_web_search import AIWebSearch
        return AIWebSearch(search_query, configured_tool, self)

    def currency_alert_service(self, target_chat_id: str | None) -> "CurrencyAlertService":
        from features.chat.currency_alert_service import CurrencyAlertService
        return CurrencyAlertService(target_chat_id, self)

    def smart_stable_diffusion_generator(
        self,
        raw_prompt: str,
        configured_copywriter_tool: ConfiguredTool,
        configured_image_gen_tool: ConfiguredTool,
        aspect_ratio: str | None = None,
        output_size: str | None = None,
    ) -> "SmartStableDiffusionGenerator":
        from features.images.smart_stable_diffusion_generator import SmartStableDiffusionGenerator
        return SmartStableDiffusionGenerator(
            raw_prompt, configured_copywriter_tool, configured_image_gen_tool, self, aspect_ratio, output_size,
        )

    # noinspection PyMethodMayBeStatic
    def simple_stable_diffusion_generator(
        self,
        prompt: str,
        configured_tool: ConfiguredTool,
        aspect_ratio: str | None = None,
        output_size: str | None = None,
    ) -> "SimpleStableDiffusionGenerator":
        from features.images.simple_stable_diffusion_generator import SimpleStableDiffusionGenerator
        return SimpleStableDiffusionGenerator(prompt, configured_tool, self, aspect_ratio, output_size)

    # noinspection PyMethodMayBeStatic
    def image_uploader(
        self,
        binary_image: bytes | None = None,
        base64_image: str | None = None,
        expiration_s: int | None = None,
        name: str | None = None,
    ) -> "ImageUploader":
        from features.images.image_uploader import ImageUploader
        return ImageUploader(binary_image, base64_image, expiration_s, name)

    # noinspection PyMethodMayBeStatic
    def file_uploader(
        self,
        content: bytes,
        filename: str,
    ):
        from features.files.file_uploader import FileUploader
        return FileUploader(content, filename)

    def chat_image_edit_service(
        self,
        attachment_ids: list[str],
        operation_guidance: str | None,
        aspect_ratio: str | None = None,
        output_size: str | None = None,
    ) -> "ChatImageEditService":
        from features.chat.chat_image_edit_service import ChatImageEditService
        return ChatImageEditService(attachment_ids, operation_guidance, aspect_ratio, output_size, self)

    def image_editor(
        self,
        image_url: str,
        configured_tool: ConfiguredTool,
        prompt: str,
        input_mime_type: str | None = None,
        aspect_ratio: str | None = None,
        output_size: str | None = None,
    ) -> "ImageEditor":
        from features.images.image_editor import ImageEditor
        return ImageEditor(image_url, configured_tool, prompt, self, input_mime_type, aspect_ratio, output_size)

    def computer_vision_analyzer(
        self,
        job_id: str,
        image_mime_type: str,
        configured_tool: ConfiguredTool,
        image_url: str | None = None,
        image_b64: str | None = None,
        additional_context: str | None = None,
    ) -> "ComputerVisionAnalyzer":
        from features.images.computer_vision_analyzer import ComputerVisionAnalyzer
        return ComputerVisionAnalyzer(job_id, image_mime_type, configured_tool, self, image_url, image_b64, additional_context)

    def document_search(
        self,
        job_id: str,
        document_url: str,
        embedding_tool: ConfiguredTool,
        copywriter_tool: ConfiguredTool,
        additional_context: str | None = None,
    ) -> "DocumentSearch":
        from features.documents.document_search import DocumentSearch
        return DocumentSearch(job_id, document_url, embedding_tool, copywriter_tool, self, additional_context)

    def audio_transcriber(
        self,
        job_id: str,
        audio_url: str,
        transcriber_tool: ConfiguredTool,
        copywriter_tool: ConfiguredTool,
        def_extension: str | None = None,
        audio_content: bytes | None = None,
        language_name: str | None = None,
        language_iso_code: str | None = None,
    ) -> "AudioTranscriber":
        from features.audio.audio_transcriber import AudioTranscriber
        return AudioTranscriber(
            job_id, audio_url,
            transcriber_tool, copywriter_tool, self,
            def_extension, audio_content,
            language_name, language_iso_code,
        )

    def chat_attachments_analyzer(
        self,
        additional_context: str | None,
        attachment_ids: list[str],
    ) -> "ChatAttachmentsAnalyzer":
        from features.chat.chat_attachments_analyzer import ChatAttachmentsAnalyzer
        return ChatAttachmentsAnalyzer(additional_context, attachment_ids, self)

    def dev_announcements_service(
        self,
        raw_message: str,
        target_handle: str | None,
        configured_tool: ConfiguredTool,
    ) -> "DevAnnouncementsService":
        from features.chat.dev_announcements_service import DevAnnouncementsService
        return DevAnnouncementsService(raw_message, target_handle, configured_tool, self)

    def sys_announcements_service(
        self,
        raw_information: str,
        target_chat: ChatConfig,
        configured_tool: ConfiguredTool,
    ) -> "SysAnnouncementsService":
        from features.announcements.sys_announcements_service import SysAnnouncementsService
        return SysAnnouncementsService(raw_information, target_chat, configured_tool, self)

    def release_summary_service(
        self,
        raw_notes: str,
        target_chat: ChatConfig | None,
        configured_tool: ConfiguredTool,
    ) -> "ReleaseSummaryService":
        from features.announcements.release_summary_service import ReleaseSummaryService
        return ReleaseSummaryService(raw_notes, target_chat, configured_tool, self)

    def user_support_service(
        self,
        user_input: str,
        github_author: str | None,
        include_platform_handle: bool,
        include_full_name: bool,
        request_type_str: str | None,
        configured_tool: ConfiguredTool,
    ) -> "UserSupportService":
        from features.support.user_support_service import UserSupportService
        return UserSupportService(
            user_input, github_author,
            include_platform_handle, include_full_name,
            request_type_str, configured_tool, self,
        )
