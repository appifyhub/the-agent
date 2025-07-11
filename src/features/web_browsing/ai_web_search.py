from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_perplexity import ChatPerplexity

from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import SONAR
from features.external_tools.tool_choice_resolver import ConfiguredTool
from features.prompting import prompt_library
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


# Not tested as it's just a proxy
class AIWebSearch(SafePrinterMixin):

    DEFAULT_TOOL: ExternalTool = SONAR
    TOOL_TYPE: ToolType = ToolType.search

    __llm_input: list[BaseMessage]
    __llm: BaseChatModel

    def __init__(self, search_query: str, configured_tool: ConfiguredTool):
        super().__init__(config.verbose)
        self.__llm_input = []
        self.__llm_input.append(SystemMessage(prompt_library.sentient_web_explorer))
        self.__llm_input.append(HumanMessage(search_query))

        tool, token = configured_tool
        self.__llm = ChatPerplexity(
            model = tool.id,
            max_tokens = 1024,
            timeout = float(config.web_timeout_s) * 3,  # search takes much longer than simple chat
            max_retries = config.web_retries,
            api_key = token,
        )

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
