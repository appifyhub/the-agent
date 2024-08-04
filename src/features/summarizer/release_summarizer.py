from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage, HumanMessage

from features.prompting import predefined_prompts
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

ANTHROPIC_AI_MODEL = "claude-3-5-sonnet-20240620"
ANTHROPIC_AI_TEMPERATURE = 0.7
ANTHROPIC_MAX_TOKENS = 500


class ReleaseSummarizer(SafePrinterMixin):
    __llm_input: list[BaseMessage]
    __llm: BaseChatModel

    def __init__(self, raw_notes: str, language_name: str | None = None, language_iso_code: str | None = None):
        super().__init__(config.verbose)
        prompt = predefined_prompts.translated_response(
            base_prompt = predefined_prompts.announcer_release_telegram,
            language_name = language_name,
            langauge_iso_code = language_iso_code,
        )
        self.__llm_input = []
        self.__llm_input.append(SystemMessage(prompt))
        self.__llm_input.append(HumanMessage(raw_notes))
        # noinspection PyArgumentList
        self.__llm = ChatAnthropic(
            model_name = ANTHROPIC_AI_MODEL,
            temperature = ANTHROPIC_AI_TEMPERATURE,
            max_tokens = ANTHROPIC_MAX_TOKENS,
            timeout = float(config.web_timeout_s),
            max_retries = config.web_retries,
            api_key = str(config.anthropic_token),
        )

    def execute(self) -> AIMessage:
        self.sprint(f"Starting release summarizer for {self.__llm_input[-1].content.replace('\n', ' \\n ')}")
        try:
            response = self.__llm.invoke(self.__llm_input)
            if not isinstance(response, AIMessage):
                raise AssertionError(f"Received a non-AI message from LLM: {response}")
            self.sprint(f"Finished summarizing, summary size is {len(response.content)} characters")
            return response
        except Exception as e:
            self.sprint(f"Release summarization failed", e)
            raise e
