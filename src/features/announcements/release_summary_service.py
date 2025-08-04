from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from db.schema.chat_config import ChatConfig
from di.di import DI
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import CLAUDE_4_SONNET
from features.external_tools.tool_choice_resolver import ConfiguredTool
from features.prompting import prompt_library
from util import log


# Not tested as it's just a proxy
class ReleaseSummaryService:

    DEFAULT_TOOL: ExternalTool = CLAUDE_4_SONNET
    TOOL_TYPE: ToolType = ToolType.copywriting

    __llm_input: list[BaseMessage]
    __copywriter: BaseChatModel
    __di: DI

    def __init__(
        self,
        raw_notes: str,
        target_chat: str | ChatConfig | None,
        configured_tool: ConfiguredTool,
        di: DI,
    ):
        language_name: str | None = None
        language_iso_code: str | None = None
        if target_chat:
            target_chat = di.authorization_service.validate_chat(target_chat)
            language_name = target_chat.language_name
            language_iso_code = target_chat.language_iso_code

        prompt = prompt_library.translator_on_response(
            base_prompt = prompt_library.announcer_release_telegram,
            language_name = language_name,
            language_iso_code = language_iso_code,
        )
        self.__llm_input = []
        self.__llm_input.append(SystemMessage(prompt))
        self.__llm_input.append(HumanMessage(raw_notes))
        self.__copywriter = di.chat_langchain_model(configured_tool)

    def execute(self) -> AIMessage:
        log.t(f"Starting release summarizer for {str(self.__llm_input[-1].content).replace('\n', ' \\n ')}")
        try:
            response = self.__copywriter.invoke(self.__llm_input)
            if not isinstance(response, AIMessage):
                raise AssertionError(f"Received a non-AI message from LLM: {response}")
            log.d(f"Finished summarizing, summary size is {len(response.content)} characters")
            return response
        except Exception as e:
            log.e("Release summarization failed", e)
            raise e
