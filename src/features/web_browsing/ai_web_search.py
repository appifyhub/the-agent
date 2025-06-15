from uuid import UUID

from langchain_community.chat_models import ChatPerplexity
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from db.crud.user import UserCRUD
from db.schema.user import User
from features.ai_tools.external_ai_tool_library import SONAR
from features.prompting import prompt_library
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


class AIWebSearch(SafePrinterMixin):
    __llm_input: list[BaseMessage]
    __llm: BaseChatModel
    __user_dao: UserCRUD

    def __init__(self, invoker_user_id_hex: str | None, search_query: str, user_dao: UserCRUD):
        super().__init__(config.verbose)
        self.__user_dao = user_dao
        self.__llm_input = []
        self.__llm_input.append(SystemMessage(prompt_library.sentient_web_explorer))
        self.__llm_input.append(HumanMessage(search_query))
        self.__llm = ChatPerplexity(
            model = SONAR.id,
            max_tokens = 1024,
            timeout = float(config.web_timeout_s) * 3,  # search takes longer than chat
            max_retries = config.web_retries,
            api_key = str(config.perplexity_api_token),
        )
        if invoker_user_id_hex:  # system invocations don't have an invoker
            self.__validate(invoker_user_id_hex)

    def __validate(self, invoker_user_id_hex: str):
        invoker_user_db = self.__user_dao.get(UUID(hex = invoker_user_id_hex))
        if not invoker_user_db:
            message = f"Invoker '{invoker_user_id_hex}' not found"
            self.sprint(message)
            raise ValueError(message)
        User.model_validate(invoker_user_db)

    def execute(self) -> AIMessage:
        self.sprint(f"Starting AI web search for {self.__llm_input[-1].content.replace('\n', ' \\n ')}")
        try:
            response = self.__llm.invoke(self.__llm_input)
            if not isinstance(response, AIMessage):
                raise AssertionError(f"Received a non-AI message from LLM: {response}")
            self.sprint(f"Finished AI web search, result size is {len(response.content)} characters")
            return response
        except Exception as e:
            self.sprint("AI web search failed", e)
            raise e
