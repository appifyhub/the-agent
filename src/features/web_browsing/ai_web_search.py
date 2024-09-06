from uuid import UUID

from langchain_community.chat_models import ChatPerplexity
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage, HumanMessage

from db.crud.user import UserCRUD
from db.model.user import UserDB
from db.schema.user import User
from features.prompting import prompt_library
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

PERPLEXITY_AI_MODEL = "llama-3.1-sonar-large-128k-online"
PERPLEXITY_AI_TEMPERATURE = 0.7
PERPLEXITY_AI_TOKENS = 500


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
            model = PERPLEXITY_AI_MODEL,
            temperature = PERPLEXITY_AI_TEMPERATURE,
            max_tokens = PERPLEXITY_AI_TOKENS,
            timeout = float(config.web_timeout_s),
            max_retries = config.web_retries,
            api_key = str(config.perplexity_api_token),
        )
        if invoker_user_id_hex:  # system invocations don't have an invoker
            self.validate(invoker_user_id_hex)

    def validate(self, invoker_user_id_hex: str):
        invoker_user_db = self.__user_dao.get(UUID(hex = invoker_user_id_hex))
        if not invoker_user_db:
            message = f"Invoker '{invoker_user_id_hex}' not found"
            self.sprint(message)
            raise ValueError(message)
        invoker_user = User.model_validate(invoker_user_db)

        if invoker_user.group < UserDB.Group.beta:
            message = f"Invoker '{invoker_user_id_hex}' is not allowed to use AI web search"
            self.sprint(message)
            raise ValueError(message)

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
