from typing import TypeVar, Any, Tuple

from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage, AIMessage
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from db.schema.user import User
from features.chat.tools.predefined_tools import PredefinedTools
from features.command_processor import CommandProcessor
from features.prompting import predefined_prompts
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

OPEN_AI_MODEL = "gpt-4o-mini"
OPEN_AI_TEMPERATURE = 0.7
OPEN_AI_MAX_TOKENS = 600

TMessage = TypeVar('TMessage', bound = BaseMessage)  # Generic message type
TooledChatModel = Runnable[LanguageModelInput, BaseMessage]


class TelegramChatBot(SafePrinterMixin):
    __invoker: User
    __messages: list[BaseMessage]
    __raw_last_message: str
    __command_processor: CommandProcessor
    __predefined_tools: PredefinedTools
    __llm_base: BaseChatModel
    __llm_tools: TooledChatModel

    def __init__(
        self,
        invoker: User,
        messages: list[BaseMessage],
        raw_last_message: str,
        command_processor: CommandProcessor,
    ):
        super().__init__(config.verbose)
        self.__invoker = invoker
        self.__messages = []
        self.__messages.append(SystemMessage(predefined_prompts.chat_telegram))
        self.__messages.extend(messages)
        self.__raw_last_message = raw_last_message
        self.__command_processor = command_processor
        self.__predefined_tools = PredefinedTools()
        # noinspection PyArgumentList
        self.__llm_base = ChatOpenAI(
            model = OPEN_AI_MODEL,
            temperature = OPEN_AI_TEMPERATURE,
            max_tokens = OPEN_AI_MAX_TOKENS,
            timeout = float(config.web_timeout_s),
            max_retries = config.web_retries,
            api_key = str(invoker.open_ai_key),
        )
        self.__llm_tools = self.__predefined_tools.bind_tools(self.__llm_base)

    def __append(self, message: TMessage) -> TMessage:
        self.__messages.append(message)
        return message

    @property
    def __last_message(self) -> BaseMessage:
        return self.__messages[-1]

    def execute(self) -> AIMessage:
        self.sprint(f"Starting chat completion for '{self.__last_message.content}'")
        answer, status = self.__process_commands()
        if not self.__invoker.open_ai_key or status == CommandProcessor.Result.success:
            return answer
        try:
            while True:
                raw_response = self.__llm_tools.invoke(self.__messages)
                response = self.__append(raw_response)
                if not response.tool_calls:
                    self.sprint(f"No tool calls. Finishing with {type(response)}: {len(response.content)} characters")
                    if not isinstance(response, AIMessage):
                        raise AssertionError(f"Received a non-AI message from LLM: {response}")
                    return response

                for tool_call in response.tool_calls:
                    tool_id: Any = tool_call["id"]
                    tool_name: Any = tool_call["name"]
                    tool_args: Any = tool_call["args"]

                    self.sprint(f"Processing {tool_id}/'{tool_name}' tool call")
                    tool_result: str | None = self.__predefined_tools.invoke(tool_name, tool_args)
                    if not tool_result:
                        self.sprint(f"Tool {tool_name} not invoked!")
                        continue
                    self.__append(ToolMessage(tool_result, tool_call_id = tool_id))

                if not isinstance(self.__last_message, ToolMessage):
                    raise LookupError("Couldn't find tools to invoke!")
        except Exception as e:
            self.sprint(f"Chat completion failed", e)
            text = predefined_prompts.error_general_problem(str(e))
            return AIMessage(text)

    def __process_commands(self) -> Tuple[AIMessage, CommandProcessor.Result]:
        self.sprint(f"No API key found for #{self.__invoker.id}")
        result = self.__command_processor.execute(self.__raw_last_message)
        self.sprint(f"Command processing result is {result.value}")
        if result == CommandProcessor.Result.unknown:
            text = predefined_prompts.error_missing_api_key("It's not a valid format.")
        elif result == CommandProcessor.Result.failed:
            text = predefined_prompts.error_general_problem("It's not a known failure.")
        elif result == CommandProcessor.Result.success:
            text = predefined_prompts.explainer_setup_done
        else:
            raise NotImplementedError("Wild branch")
        return AIMessage(text), result
