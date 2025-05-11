from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage, HumanMessage
from pydantic import SecretStr

from features.ai_tools.external_ai_tool_library import CLAUDE_3_7_SONNET
from features.prompting import prompt_library
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


# Not tested as it's just a proxy
class ReleaseSummarizer(SafePrinterMixin):
    __llm_input: list[BaseMessage]
    __copywriter: BaseChatModel

    def __init__(self, raw_notes: str, language_name: str | None = None, language_iso_code: str | None = None):
        super().__init__(config.verbose)
        prompt = prompt_library.translator_on_response(
            base_prompt = prompt_library.announcer_release_telegram,
            language_name = language_name,
            language_iso_code = language_iso_code,
        )
        self.__llm_input = []
        self.__llm_input.append(SystemMessage(prompt))
        self.__llm_input.append(HumanMessage(raw_notes))
        # noinspection PyArgumentList
        self.__copywriter = ChatAnthropic(
            model_name = CLAUDE_3_7_SONNET.id,
            temperature = 1.0,
            max_tokens = 500,
            timeout = float(config.web_timeout_s),
            max_retries = config.web_retries,
            api_key = SecretStr(str(config.anthropic_token)),
        )

    def execute(self) -> AIMessage:
        self.sprint(f"Starting release summarizer for {self.__llm_input[-1].content.replace('\n', ' \\n ')}")
        try:
            response = self.__copywriter.invoke(self.__llm_input)
            if not isinstance(response, AIMessage):
                raise AssertionError(f"Received a non-AI message from LLM: {response}")
            self.sprint(f"Finished summarizing, summary size is {len(response.content)} characters")
            return response
        except Exception as e:
            self.sprint("Release summarization failed", e)
            raise e
