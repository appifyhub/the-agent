from uuid import UUID

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from api.authorization_service import AuthorizationService
from db.crud.chat_config import ChatConfigCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.schema.chat_config import ChatConfig
from db.schema.user import User
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.external_tools.access_token_resolver import AccessTokenResolver
from features.external_tools.external_tool_library import CLAUDE_4_SONNET
from features.prompting import prompt_library
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


# Not tested as it's just a proxy
class ReleaseSummarizer(SafePrinterMixin):
    __llm_input: list[BaseMessage]
    __copywriter: BaseChatModel

    def __init__(
        self,
        raw_notes: str,
        invoker_user: str | UUID | User,
        target_chat: str | ChatConfig | None,  # default language if None
        user_dao: UserCRUD,
        chat_config_dao: ChatConfigCRUD,
        sponsorship_dao: SponsorshipCRUD,
        telegram_bot_sdk: TelegramBotSDK,
    ):
        super().__init__(config.verbose)
        authorization_service = AuthorizationService(telegram_bot_sdk, user_dao, chat_config_dao)

        # compute language configuration
        language_name: str | None = None
        language_iso_code: str | None = None
        if target_chat:
            target_chat = authorization_service.validate_chat(target_chat)
            language_name = target_chat.language_name
            language_iso_code = target_chat.language_iso_code

        invoker_user = authorization_service.validate_user(invoker_user)
        access_token_resolver = AccessTokenResolver(invoker_user, user_dao, sponsorship_dao)
        invoker_token = access_token_resolver.get_access_token_for_tool(CLAUDE_4_SONNET)
        if not invoker_token:
            message = f"Couldn't find an access token for {CLAUDE_4_SONNET.name}"
            self.sprint(message)
            raise ValueError(message)
        prompt = prompt_library.translator_on_response(
            base_prompt = prompt_library.announcer_release_telegram,
            language_name = language_name,
            language_iso_code = language_iso_code,
        )
        # noinspection PyArgumentList
        self.__copywriter = ChatAnthropic(
            model_name = CLAUDE_4_SONNET.id,
            temperature = 1.0,
            max_tokens = 500,
            timeout = float(config.web_timeout_s),
            max_retries = config.web_retries,
            api_key = invoker_token,
        )
        self.__llm_input = []
        self.__llm_input.append(SystemMessage(prompt))
        self.__llm_input.append(HumanMessage(raw_notes))

    def execute(self) -> AIMessage:
        self.sprint(f"Starting release summarizer for {str(self.__llm_input[-1].content).replace('\n', ' \\n ')}")
        try:
            response = self.__copywriter.invoke(self.__llm_input)
            if not isinstance(response, AIMessage):
                raise AssertionError(f"Received a non-AI message from LLM: {response}")
            self.sprint(f"Finished summarizing, summary size is {len(response.content)} characters")
            return response
        except Exception as e:
            self.sprint("Release summarization failed", e)
            raise e
