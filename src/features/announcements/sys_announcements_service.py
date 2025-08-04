from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from db.schema.chat_config import ChatConfig
from di.di import DI
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import CLAUDE_3_5_SONNET
from features.external_tools.tool_choice_resolver import ConfiguredTool
from features.prompting import prompt_library
from util import log


# Not tested as it's just a proxy
class SysAnnouncementsService:

    DEFAULT_TOOL: ExternalTool = CLAUDE_3_5_SONNET
    TOOL_TYPE: ToolType = ToolType.copywriting

    __llm_input: list[BaseMessage]
    __copywriter: BaseChatModel

    def __init__(
        self,
        raw_information: str,
        target_chat: str | ChatConfig,
        configured_tool: ConfiguredTool,
        di: DI,
    ):
        target_chat = di.authorization_service.validate_chat(target_chat)
        prompt = prompt_library.translator_on_response(
            base_prompt = prompt_library.announcer_event_telegram,
            language_name = target_chat.language_name,
            language_iso_code = target_chat.language_iso_code,
        )
        self.__copywriter = di.chat_langchain_model(configured_tool)
        self.__llm_input = []
        self.__llm_input.append(SystemMessage(prompt))
        self.__llm_input.append(HumanMessage(raw_information))

    def execute(self) -> AIMessage:
        log.t(f"Starting information announcer for {str(self.__llm_input[-1].content).replace('\n', ' \\n ')}")
        try:
            response = self.__copywriter.invoke(self.__llm_input)
            if not isinstance(response, AIMessage):
                raise AssertionError(f"Received a non-AI message from LLM: {response}")
            log.d(f"Finished announcement creation, summary size is {len(response.content)} characters")
            return response
        except Exception as e:
            log.e("Information announcement failed", e)
            raise e
