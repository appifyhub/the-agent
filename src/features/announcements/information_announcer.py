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
from features.external_tools.external_tool_library import CLAUDE_3_5_SONNET
from features.prompting import prompt_library
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


# Not tested as it's just a proxy
class InformationAnnouncer(SafePrinterMixin):
    __llm_input: list[BaseMessage]
    __copywriter: BaseChatModel

    def __init__(
        self,
        raw_information: str,
        invoker: str | UUID | User,
        target_chat: str | ChatConfig,
        user_dao: UserCRUD,
        chat_config_dao: ChatConfigCRUD,
        sponsorship_dao: SponsorshipCRUD,
        telegram_bot_sdk: TelegramBotSDK,
    ):
        super().__init__(config.verbose)
        authorization_service = AuthorizationService(telegram_bot_sdk, user_dao, chat_config_dao)
        target_chat = authorization_service.validate_chat(target_chat)
        prompt = prompt_library.translator_on_response(
            base_prompt = prompt_library.announcer_event_telegram,
            language_name = target_chat.language_name,
            language_iso_code = target_chat.language_iso_code,
        )
        invoker = authorization_service.validate_user(invoker)
        access_token_resolver = AccessTokenResolver(invoker, user_dao, sponsorship_dao)
        invoker_token = access_token_resolver.require_access_token_for_tool(CLAUDE_3_5_SONNET)
        # noinspection PyArgumentList
        self.__copywriter = ChatAnthropic(
            model_name = CLAUDE_3_5_SONNET.id,
            temperature = 0.5,
            max_tokens = 500,
            timeout = float(config.web_timeout_s),
            max_retries = config.web_retries,
            api_key = invoker_token,
        )
        self.__llm_input = []
        self.__llm_input.append(SystemMessage(prompt))
        self.__llm_input.append(HumanMessage(raw_information))

    def execute(self) -> AIMessage:
        self.sprint(f"Starting information announcer for {self.__llm_input[-1].content.replace('\n', ' \\n ')}")
        try:
            response = self.__copywriter.invoke(self.__llm_input)
            if not isinstance(response, AIMessage):
                raise AssertionError(f"Received a non-AI message from LLM: {response}")
            self.sprint(f"Finished announcement creation, summary size is {len(response.content)} characters")
            return response
        except Exception as e:
            self.sprint("Information announcement failed", e)
            raise e
