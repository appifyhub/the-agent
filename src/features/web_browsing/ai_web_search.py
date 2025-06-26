from uuid import UUID

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_perplexity import ChatPerplexity

from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.schema.user import User
from features.external_tools.access_token_resolver import AccessTokenResolver
from features.external_tools.external_tool_library import SONAR
from features.prompting import prompt_library
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


class AIWebSearch(SafePrinterMixin):
    __llm_input: list[BaseMessage]
    __llm: BaseChatModel
    __user_dao: UserCRUD
    __invoker: User

    def __init__(
        self,
        invoker_user_id_hex: str,
        search_query: str,
        user_dao: UserCRUD,
        sponsorship_dao: SponsorshipCRUD,
    ):
        super().__init__(config.verbose)
        self.__user_dao = user_dao
        self.__llm_input = []
        self.__llm_input.append(SystemMessage(prompt_library.sentient_web_explorer))
        self.__llm_input.append(HumanMessage(search_query))

        self.__validate(invoker_user_id_hex)
        token_resolver = AccessTokenResolver(
            user_dao = user_dao,
            sponsorship_dao = sponsorship_dao,
            invoker_user = self.__invoker,
        )

        resolved_token = token_resolver.require_access_token_for_tool(SONAR)
        self.__llm = ChatPerplexity(
            model = SONAR.id,
            max_tokens = 1024,
            timeout = float(config.web_timeout_s) * 3,  # search takes much longer than simple chat
            max_retries = config.web_retries,
            api_key = resolved_token,
        )

    def __validate(self, invoker_user_id_hex: str):
        invoker_user_db = self.__user_dao.get(UUID(hex = invoker_user_id_hex))
        if not invoker_user_db:
            message = f"Invoker '{invoker_user_id_hex}' not found"
            self.sprint(message)
            raise ValueError(message)
        self.__invoker = User.model_validate(invoker_user_db)

    def execute(self) -> AIMessage:
        content_preview = str(self.__llm_input[-1].content).replace("\n", " \\n ")
        self.sprint(f"Starting AI web search for {content_preview}")
        try:
            response = self.__llm.invoke(self.__llm_input)
            if not isinstance(response, AIMessage):
                raise AssertionError(f"Received a non-AI message from LLM: {response}")
            self.sprint(f"Finished AI web search, result size is {len(response.content)} characters")
            return response
        except Exception as e:
            self.sprint("AI web search failed", e)
            raise e
