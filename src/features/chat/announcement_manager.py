from datetime import datetime
from uuid import UUID

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from api.authorization_service import AuthorizationService
from db.crud.chat_config import ChatConfigCRUD
from db.crud.chat_message import ChatMessageCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.model.user import UserDB
from db.schema.chat_config import ChatConfig
from db.schema.chat_message import ChatMessageSave
from db.schema.user import User
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.external_tools.access_token_resolver import AccessTokenResolver
from features.external_tools.external_tool_library import CLAUDE_3_5_SONNET
from features.prompting import prompt_library
from util.config import config
from util.functions import construct_bot_message_id
from util.safe_printer_mixin import SafePrinterMixin
from util.translations_cache import TranslationsCache


class AnnouncementManager(SafePrinterMixin):
    __raw_message: str
    __translations: TranslationsCache
    __telegram_bot_sdk: TelegramBotSDK
    __user_dao: UserCRUD
    __chat_config_dao: ChatConfigCRUD
    __chat_message_dao: ChatMessageCRUD
    __copywriter: BaseChatModel
    __invoker_user: User
    __target_chat: ChatConfig | None

    def __init__(
        self,
        raw_message: str,
        invoker_user: str | UUID | User,
        target_telegram_username: str | None,
        user_dao: UserCRUD,
        chat_config_dao: ChatConfigCRUD,
        chat_message_dao: ChatMessageCRUD,
        sponsorship_dao: SponsorshipCRUD,
        telegram_bot_sdk: TelegramBotSDK,
        translations: TranslationsCache,
    ):
        super().__init__(config.verbose)
        self.__raw_message = raw_message
        self.__translations = translations
        self.__telegram_bot_sdk = telegram_bot_sdk
        self.__user_dao = user_dao
        self.__chat_config_dao = chat_config_dao
        self.__chat_message_dao = chat_message_dao

        authorization_service = AuthorizationService(telegram_bot_sdk, user_dao, chat_config_dao)
        self.__invoker_user = authorization_service.validate_user(invoker_user)
        self.__validate(target_telegram_username)

        token_resolver = AccessTokenResolver(self.__invoker_user, user_dao, sponsorship_dao)
        invoker_token = token_resolver.require_access_token_for_tool(CLAUDE_3_5_SONNET)

        # noinspection PyArgumentList
        self.__copywriter = ChatAnthropic(
            model_name = CLAUDE_3_5_SONNET.id,
            temperature = 0.5,
            max_tokens = 500,
            timeout = float(config.web_timeout_s),
            max_retries = config.web_retries,
            api_key = invoker_token,
        )

    def __validate(self, target_telegram_username: str | None):
        self.sprint("Validating invoker permissions")
        if self.__invoker_user.group < UserDB.Group.developer:
            message = f"Invoker '{self.__invoker_user.id.hex}' is not a developer"
            self.sprint(message)
            raise ValueError(message)

        self.sprint("Validating target user data")
        self.__target_chat = None
        if target_telegram_username:
            target_user_db = self.__user_dao.get_by_telegram_username(target_telegram_username)
            if not target_user_db:
                message = f"Target user '{target_telegram_username}' not found"
                self.sprint(message)
                raise ValueError(message)
            target_user = User.model_validate(target_user_db)
            if not target_user.telegram_chat_id:
                message = f"Target user '{target_telegram_username}' has no private chat ID yet"
                self.sprint(message)
                raise ValueError(message)
            target_chat_db = self.__chat_config_dao.get(target_user.telegram_chat_id)
            if not target_chat_db:
                message = f"Target chat '{target_user.telegram_chat_id}' not found"
                self.sprint(message)
                raise ValueError(message)
            self.__target_chat = ChatConfig.model_validate(target_chat_db)

    def execute(self) -> dict:
        self.sprint(f"Executing announcement from {self.__invoker_user.telegram_username}")
        target_chats: list[ChatConfig]
        if self.__target_chat:
            self.sprint(f"Target chat: {self.__target_chat.chat_id}")
            target_chats = [self.__target_chat]
        else:
            self.sprint("Target chats: all")
            target_chats_db = self.__chat_config_dao.get_all(limit = 2048)
            target_chats = [ChatConfig.model_validate(chat) for chat in target_chats_db]
        summaries_created: int = 0
        chats_notified: int = 0

        # translate for default language
        try:
            answer = self.__create_announcement(target_chat = None)
            self.__translations.save(str(answer.content))
            summaries_created += 1
        except Exception as e:
            self.sprint("Announcement translation failed for default language", e)

        # translate and notify for each chat
        for chat in target_chats:
            try:
                summary = self.__translations.get(chat.language_name, chat.language_iso_code)
                if not summary:
                    answer = self.__create_announcement(chat)
                    summary = self.__translations.save(str(answer.content), chat.language_name, chat.language_iso_code)
                    summaries_created += 1
                self.__notify_chat(chat, summary)
                chats_notified += 1
            except Exception as e:
                self.sprint(f"Announcement failed for chat #{chat.chat_id}", e)

        self.sprint(f"Chats: {len(target_chats)}, summaries created: {summaries_created}, notified: {chats_notified}")
        return {
            "chats_selected": len(target_chats),
            "chats_notified": chats_notified,
            "summaries_created": summaries_created,
        }

    def __create_announcement(self, target_chat: ChatConfig | None) -> AIMessage:
        target_chat = self.__target_chat if not target_chat else target_chat
        base_prompt = (
            prompt_library.developers_announcer_telegram
            if not target_chat
            else prompt_library.developers_message_deliverer
        )
        prompt = prompt_library.translator_on_response(
            base_prompt = base_prompt,
            language_name = target_chat.language_name if target_chat else None,
            language_iso_code = target_chat.language_iso_code if target_chat else None,
        )
        messages = [
            SystemMessage(prompt),
            HumanMessage(self.__raw_message),
        ]
        response = self.__copywriter.invoke(messages)
        if not isinstance(response, AIMessage):
            raise AssertionError(f"Received a non-AI message from LLM: {response}")
        return response

    def __notify_chat(self, chat: ChatConfig, summary: str):
        self.__telegram_bot_sdk.send_text_message(chat.chat_id, summary)
        sent_at = datetime.now()
        message_to_store = ChatMessageSave(
            chat_id = chat.chat_id,
            message_id = construct_bot_message_id(chat.chat_id, sent_at),
            author_id = prompt_library.TELEGRAM_BOT_USER.id,
            sent_at = sent_at,
            text = summary,
        )
        self.__chat_message_dao.save(message_to_store)
