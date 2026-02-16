from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from di.di import DI
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import SONAR
from features.external_tools.configured_tool import ConfiguredTool
from features.integrations import prompt_resolvers
from util import log


# Not tested as it's just a proxy
class AIWebSearch:

    DEFAULT_TOOL: ExternalTool = SONAR
    TOOL_TYPE: ToolType = ToolType.search

    __llm_input: list[BaseMessage]
    __llm: BaseChatModel

    def __init__(self, search_query: str, configured_tool: ConfiguredTool, di: DI):
        system_prompt = prompt_resolvers.sentient_web_search(di.invoker_chat)
        self.__llm_input = [SystemMessage(system_prompt), HumanMessage(search_query)]
        self.__llm = di.chat_langchain_model(configured_tool)

    def execute(self) -> AIMessage:
        content_preview = str(self.__llm_input[-1].content).replace("\n", " \\n ")
        log.t(f"Starting AI web search for {content_preview}")
        try:
            response = self.__llm.invoke(self.__llm_input)
            if not isinstance(response, AIMessage):
                raise AssertionError(f"Received a non-AI message from LLM: {response}")
            log.d(f"Finished AI web search, result size is {len(response.content)} characters")
            return response
        except Exception as e:
            log.e("AI web search failed", e)
            raise e
