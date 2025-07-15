from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from pydantic import SecretStr
from sqlalchemy.orm import Session

from db.schema.chat_config import ChatConfig
from db.schema.user import User
from features.chat.telegram.telegram_progress_notifier import (
    DEFAULT_REACTION_INTERVAL_S,
    DEFAULT_TEXT_UPDATE_INTERVAL_S,
)
from features.llm import langchain_creator

if TYPE_CHECKING:
    from api.authorization_service import AuthorizationService
    from api.settings_controller import SettingsController
    from api.sponsorships_controller import SponsorshipsController
    from db.crud.chat_config import ChatConfigCRUD
    from db.crud.chat_message import ChatMessageCRUD
    from db.crud.chat_message_attachment import ChatMessageAttachmentCRUD
    from db.crud.price_alert import PriceAlertCRUD
    from db.crud.sponsorship import SponsorshipCRUD
    from db.crud.tools_cache import ToolsCacheCRUD
    from db.crud.user import UserCRUD
    from features.announcements.information_announcer import InformationAnnouncer
    from features.announcements.release_summarizer import ReleaseSummarizer
    from features.audio.audio_transcriber import AudioTranscriber
    from features.chat.attachments_describer import AttachmentsDescriber
    from features.chat.chat_image_gen_service import ChatImageGenService
    from features.chat.command_processor import CommandProcessor
    from features.chat.dev_announcements_service import DevAnnouncementsService
    from features.chat.image_generator import ImageGenerator
    from features.chat.price_alert_manager import PriceAlertManager
    from features.chat.telegram.domain_langchain_mapper import DomainLangchainMapper
    from features.chat.telegram.sdk.telegram_bot_api import TelegramBotAPI
    from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
    from features.chat.telegram.telegram_chat_bot import TelegramChatBot
    from features.chat.telegram.telegram_data_resolver import TelegramDataResolver
    from features.chat.telegram.telegram_domain_mapper import TelegramDomainMapper
    from features.chat.telegram.telegram_progress_notifier import TelegramProgressNotifier
    from features.currencies.exchange_rate_fetcher import ExchangeRateFetcher
    from features.documents.document_search import DocumentSearch
    from features.external_tools.access_token_resolver import AccessTokenResolver
    from features.external_tools.tool_choice_resolver import ConfiguredTool, ToolChoiceResolver
    from features.images.computer_vision_analyzer import ComputerVisionAnalyzer
    from features.images.image_background_remover import ImageBackgroundRemover
    from features.images.image_contents_restorer import ImageContentsRestorer
    from features.images.image_editor import ImageEditor
    from features.images.text_stable_diffusion_generator import TextStableDiffusionGenerator
    from features.sponsorships.sponsorship_service import SponsorshipService
    from features.support.user_support_manager import UserSupportManager
    from features.web_browsing.ai_web_search import AIWebSearch
    from features.web_browsing.html_content_cleaner import HTMLContentCleaner
    from features.web_browsing.twitter_status_fetcher import TwitterStatusFetcher
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
    _telegram_bot_sdk: "TelegramBotSDK | None"
    # Repositories
    _user_crud: "UserCRUD | None"
    _chat_config_crud: "ChatConfigCRUD | None"
    _chat_message_crud: "ChatMessageCRUD | None"
    _chat_message_attachment_crud: "ChatMessageAttachmentCRUD | None"
    _sponsorship_crud: "SponsorshipCRUD | None"
    _tools_cache_crud: "ToolsCacheCRUD | None"
    _price_alert_crud: "PriceAlertCRUD | None"
    # Services
    _sponsorship_service: "SponsorshipService | None"
    _authorization_service: "AuthorizationService | None"
    # Controllers
    _settings_controller: "SettingsController | None"
    _sponsorships_controller: "SponsorshipsController | None"
    # Internal tools
    _access_token_resolver: "AccessTokenResolver | None"
    _tool_choice_resolver: "ToolChoiceResolver | None"
    _telegram_domain_mapper: "TelegramDomainMapper | None"
    _domain_langchain_mapper: "DomainLangchainMapper | None"
    _telegram_data_resolver: "TelegramDataResolver | None"
    # Features
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
        self._telegram_bot_sdk = None
        # Repositories
        self._user_crud = None
        self._chat_config_crud = None
        self._chat_message_crud = None
        self._chat_message_attachment_crud = None
        self._sponsorship_crud = None
        self._tools_cache_crud = None
        self._price_alert_crud = None
        # Services
        self._sponsorship_service = None
        self._authorization_service = None
        # Controllers
        self._settings_controller = None
        self._sponsorships_controller = None
        # Internal tools
        self._access_token_resolver = None
        self._tool_choice_resolver = None
        self._telegram_domain_mapper = None
        self._domain_langchain_mapper = None
        self._telegram_data_resolver = None
        # Features
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
    def invoker_chat(self) -> ChatConfig:
        if self._invoker_chat is None:
            try:
                self._invoker_chat = self.authorization_service.validate_chat(self.invoker_chat_id)
            except Exception as e:
                raise ConstructorDependencyNotMetError(f"Invoker chat validation failed: {e}")
        return self._invoker_chat

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
        if self._invoker_chat and self._invoker_chat.chat_id != invoker_chat_id:
            self._invoker_chat = None

    def inject_invoker_chat(self, invoker_chat: ChatConfig | None):
        if not invoker_chat:
            self._invoker_chat = None
            self._invoker_chat_id = None
            return
        self._invoker_chat = invoker_chat
        if not self._invoker_chat_id or self._invoker_chat_id != invoker_chat.chat_id:
            self._invoker_chat_id = invoker_chat.chat_id

    # === SDKs ===

    @property
    def telegram_bot_api(self) -> "TelegramBotAPI":
        if self._telegram_bot_api is None:
            from features.chat.telegram.sdk.telegram_bot_api import TelegramBotAPI
            self._telegram_bot_api = TelegramBotAPI()
        return self._telegram_bot_api

    @property
    def telegram_bot_sdk(self) -> "TelegramBotSDK":
        if self._telegram_bot_sdk is None:
            from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
            self._telegram_bot_sdk = TelegramBotSDK(self.db, self.telegram_bot_api)
        return self._telegram_bot_sdk

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

    # === Services ===

    @property
    def sponsorship_service(self) -> "SponsorshipService":
        if self._sponsorship_service is None:
            from features.sponsorships.sponsorship_service import SponsorshipService
            self._sponsorship_service = SponsorshipService(self.user_crud, self.sponsorship_crud)
        return self._sponsorship_service

    @property
    def authorization_service(self) -> "AuthorizationService":
        if self._authorization_service is None:
            from api.authorization_service import AuthorizationService
            self._authorization_service = AuthorizationService(self.telegram_bot_sdk, self.user_crud, self.chat_config_crud)
        return self._authorization_service

    # === Controllers ===

    @property
    def settings_controller(self) -> "SettingsController":
        if self._settings_controller is None:
            from api.settings_controller import SettingsController
            self._settings_controller = SettingsController(
                self.invoker_id,
                self.telegram_bot_sdk,
                self.user_crud,
                self.chat_config_crud,
                self.sponsorship_crud,
            )
        return self._settings_controller

    @property
    def sponsorships_controller(self) -> "SponsorshipsController":
        if self._sponsorships_controller is None:
            from api.sponsorships_controller import SponsorshipsController
            self._sponsorships_controller = SponsorshipsController(
                self.invoker_id,
                self.user_crud,
                self.sponsorship_crud,
                self.telegram_bot_sdk,
                self.chat_config_crud,
            )
        return self._sponsorships_controller

    # === Internal tools ===

    @property
    def access_token_resolver(self) -> "AccessTokenResolver":
        if self._access_token_resolver is None:
            from features.external_tools.access_token_resolver import AccessTokenResolver
            self._access_token_resolver = AccessTokenResolver(self.invoker, self.user_crud, self.sponsorship_crud)
        return self._access_token_resolver

    @property
    def tool_choice_resolver(self) -> "ToolChoiceResolver":
        if self._tool_choice_resolver is None:
            from features.external_tools.tool_choice_resolver import ToolChoiceResolver
            self._tool_choice_resolver = ToolChoiceResolver(self.invoker, self.access_token_resolver)
        return self._tool_choice_resolver

    @property
    def translations_cache(self) -> "TranslationsCache":
        from util.translations_cache import TranslationsCache
        return TranslationsCache()

    @property
    def telegram_domain_mapper(self) -> "TelegramDomainMapper":
        if self._telegram_domain_mapper is None:
            from features.chat.telegram.telegram_domain_mapper import TelegramDomainMapper
            self._telegram_domain_mapper = TelegramDomainMapper()
        return self._telegram_domain_mapper

    @property
    def domain_langchain_mapper(self) -> "DomainLangchainMapper":
        if self._domain_langchain_mapper is None:
            from features.chat.telegram.domain_langchain_mapper import DomainLangchainMapper
            self._domain_langchain_mapper = DomainLangchainMapper()
        return self._domain_langchain_mapper

    @property
    def telegram_data_resolver(self) -> "TelegramDataResolver":
        if self._telegram_data_resolver is None:
            from features.chat.telegram.telegram_data_resolver import TelegramDataResolver
            self._telegram_data_resolver = TelegramDataResolver(self.db, self.telegram_bot_api)
        return self._telegram_data_resolver

    # === Features ===

    # noinspection PyMethodMayBeStatic
    def chat_langchain_model(self, configured_tool: ConfiguredTool) -> "BaseChatModel":
        return langchain_creator.create(configured_tool)

    def telegram_progress_notifier(
        self,
        message_id: str,
        auto_start: bool = False,
        reaction_interval_s: int = DEFAULT_REACTION_INTERVAL_S,
        text_update_interval_s: int = DEFAULT_TEXT_UPDATE_INTERVAL_S,
    ) -> "TelegramProgressNotifier":
        from features.chat.telegram.telegram_progress_notifier import TelegramProgressNotifier
        return TelegramProgressNotifier(
            self.invoker_chat,
            message_id,
            self.telegram_bot_sdk,
            auto_start,
            reaction_interval_s,
            text_update_interval_s,
        )

    def telegram_chat_bot(
        self,
        messages: list[BaseMessage],
        attachment_ids: list[str],
        raw_last_message: str,
        message_id: str,
        auto_start: bool = False,
        reaction_interval_s: int = DEFAULT_REACTION_INTERVAL_S,
        text_update_interval_s: int = DEFAULT_TEXT_UPDATE_INTERVAL_S,
    ) -> "TelegramChatBot":
        from features.chat.telegram.telegram_chat_bot import TelegramChatBot
        return TelegramChatBot(
            self.invoker_chat,
            self.invoker,
            messages,
            attachment_ids,
            raw_last_message,
            self.command_processor,
            self.telegram_progress_notifier(message_id, auto_start, reaction_interval_s, text_update_interval_s),
            self.access_token_resolver,
        )

    @property
    def command_processor(self) -> "CommandProcessor":
        if self._command_processor is None:
            from features.chat.command_processor import CommandProcessor
            self._command_processor = CommandProcessor(
                self.invoker,
                self.user_crud,
                self.sponsorship_service,
                self.settings_controller,
                self.telegram_bot_sdk,
            )
        return self._command_processor

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
            url,
            self,
            headers,
            params,
            cache_ttl_html,
            cache_ttl_json,
            auto_fetch_html,
            auto_fetch_json,
        )

    def html_content_cleaner(self, raw_html: str) -> "HTMLContentCleaner":
        from features.web_browsing.html_content_cleaner import HTMLContentCleaner
        return HTMLContentCleaner(raw_html, self.tools_cache_crud)

    def twitter_status_fetcher(self, tweet_id: str) -> "TwitterStatusFetcher":
        from features.web_browsing.twitter_status_fetcher import TwitterStatusFetcher
        return TwitterStatusFetcher(
            tweet_id,
            self.invoker,
            self.tools_cache_crud,
            self.user_crud,
            self.chat_config_crud,
            self.sponsorship_crud,
            self.telegram_bot_sdk,
        )

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

    def price_alert_manager(self, target_chat_id: str | None) -> "PriceAlertManager":
        from features.chat.price_alert_manager import PriceAlertManager
        return PriceAlertManager(target_chat_id, self)

    def chat_image_gen_service(
        self,
        raw_prompt: str,
        configured_copywriter_tool: ConfiguredTool,
        configured_image_gen_tool: ConfiguredTool,
    ) -> "ChatImageGenService":
        from features.chat.chat_image_gen_service import ChatImageGenService
        return ChatImageGenService(raw_prompt, configured_copywriter_tool, configured_image_gen_tool, self)

    # noinspection PyMethodMayBeStatic
    def text_stable_diffusion_generator(
        self,
        prompt: str,
        configured_tool: ConfiguredTool,
    ) -> "TextStableDiffusionGenerator":
        from features.images.text_stable_diffusion_generator import TextStableDiffusionGenerator
        return TextStableDiffusionGenerator(prompt, configured_tool)

    def image_generator(
        self,
        attachment_ids: list[str],
        operation_name: str,
        operation_guidance: str | None,
    ) -> "ImageGenerator":
        from features.chat.image_generator import ImageGenerator
        return ImageGenerator(attachment_ids, operation_name, operation_guidance, self)

    # noinspection PyMethodMayBeStatic
    def image_editor(
        self,
        image_url: str,
        replicate_api_key: SecretStr,
        context: str | None = None,
        mime_type: str | None = None,
    ) -> "ImageEditor":
        from features.images.image_editor import ImageEditor
        return ImageEditor(image_url, replicate_api_key, context, mime_type)

    # noinspection PyMethodMayBeStatic
    def image_background_remover(
        self,
        image_url: str,
        replicate_api_key: SecretStr,
        mime_type: str | None = None,
    ) -> "ImageBackgroundRemover":
        from features.images.image_background_remover import ImageBackgroundRemover
        return ImageBackgroundRemover(image_url, replicate_api_key, mime_type)

    # noinspection PyMethodMayBeStatic
    def image_contents_restorer(
        self,
        image_url: str,
        replicate_api_key: SecretStr,
        prompt_positive: str | None = None,
        prompt_negative: str | None = None,
        mime_type: str | None = None,
    ) -> "ImageContentsRestorer":
        from features.images.image_contents_restorer import ImageContentsRestorer
        return ImageContentsRestorer(
            image_url,
            replicate_api_key,
            prompt_positive,
            prompt_negative,
            mime_type,
        )

    # noinspection PyMethodMayBeStatic
    def computer_vision_analyzer(
        self,
        job_id: str,
        image_mime_type: str,
        open_ai_api_key: SecretStr,
        image_url: str | None = None,
        image_b64: str | None = None,
        additional_context: str | None = None,
    ) -> "ComputerVisionAnalyzer":
        from features.images.computer_vision_analyzer import ComputerVisionAnalyzer
        return ComputerVisionAnalyzer(
            job_id,
            image_mime_type,
            open_ai_api_key,
            image_url,
            image_b64,
            additional_context,
        )

    # noinspection PyMethodMayBeStatic
    def document_search(
        self,
        job_id: str,
        document_url: str,
        open_ai_api_key: SecretStr,
        anthropic_token: SecretStr,
        additional_context: str | None = None,
    ) -> "DocumentSearch":
        from features.documents.document_search import DocumentSearch
        return DocumentSearch(job_id, document_url, open_ai_api_key, anthropic_token, additional_context)

    # noinspection PyMethodMayBeStatic
    def audio_transcriber(
        self,
        job_id: str,
        audio_url: str,
        open_ai_api_key: SecretStr,
        anthropic_token: SecretStr,
        def_extension: str | None = None,
        audio_content: bytes | None = None,
        language_name: str | None = None,
        language_iso_code: str | None = None,
    ) -> "AudioTranscriber":
        from features.audio.audio_transcriber import AudioTranscriber
        return AudioTranscriber(
            job_id,
            audio_url,
            open_ai_api_key,
            anthropic_token,
            def_extension,
            audio_content,
            language_name,
            language_iso_code,
        )

    def attachments_describer(
        self,
        additional_context: str | None,
        attachment_ids: list[str],
    ) -> "AttachmentsDescriber":
        from features.chat.attachments_describer import AttachmentsDescriber
        return AttachmentsDescriber(additional_context, attachment_ids, self)

    def dev_announcements_service(
        self,
        raw_message: str,
        target_telegram_username: str | None,
        configured_tool: ConfiguredTool,
    ) -> "DevAnnouncementsService":
        from features.chat.dev_announcements_service import DevAnnouncementsService
        return DevAnnouncementsService(raw_message, target_telegram_username, configured_tool, self)

    def information_announcer(
        self,
        raw_information: str,
        target_chat: str | ChatConfig,
    ) -> "InformationAnnouncer":
        from features.announcements.information_announcer import InformationAnnouncer
        return InformationAnnouncer(
            raw_information,
            self.invoker_id,
            target_chat,
            self.user_crud,
            self.chat_config_crud,
            self.sponsorship_crud,
            self.telegram_bot_sdk,
        )

    def release_summarizer(
        self,
        raw_notes: str,
        target_chat: str | ChatConfig | None = None,
    ) -> "ReleaseSummarizer":
        from features.announcements.release_summarizer import ReleaseSummarizer
        return ReleaseSummarizer(
            raw_notes,
            self.invoker_id,
            target_chat,
            self.user_crud,
            self.chat_config_crud,
            self.sponsorship_crud,
            self.telegram_bot_sdk,
        )

    def user_support_manager(
        self,
        user_input: str,
        invoker_github_username: str | None,
        include_telegram_username: bool,
        include_full_name: bool,
        request_type_str: str | None,
    ) -> "UserSupportManager":
        from features.support.user_support_manager import UserSupportManager
        return UserSupportManager(
            user_input,
            self.invoker_id,
            invoker_github_username,
            include_telegram_username,
            include_full_name,
            request_type_str,
            self.user_crud,
            self.chat_config_crud,
            self.sponsorship_crud,
            self.telegram_bot_sdk,
        )
