import uuid
from typing import TypeVar, Any

from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage, AIMessage
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from db.model.user import UserDB
from db.schema.user import User, UserSave
from features.chat.tools.predefined_tools import PredefinedTools
from features.prompting import predefined_prompts
from features.prompting.predefined_prompts import MULTI_MESSAGE_DELIMITER
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

OPEN_AI_MODEL = "gpt-4o-mini"
OPEN_AI_TEMPERATURE = 0.7
OPEN_AI_MAX_TOKENS = 600

TMessage = TypeVar('TMessage', bound = BaseMessage)  # Generic message type
TooledChatModel = Runnable[LanguageModelInput, BaseMessage]

TELEGRAM_BOT_USER = UserSave(
    full_name = config.telegram_bot_name,
    telegram_username = config.telegram_bot_username,
    telegram_chat_id = config.telegram_bot_username,
    telegram_user_id = abs(hash(config.telegram_bot_username)) % (2 ** 31 - 1),
    open_ai_key = None,
    group = UserDB.Group.standard,
    id = uuid.uuid5(uuid.NAMESPACE_DNS, config.telegram_bot_username),
)


class TelegramChatBot(SafePrinterMixin):
    __prompt: BaseMessage
    __messages: list[BaseMessage]
    __invoker: User
    __predefined_tools: PredefinedTools
    __llm_base: BaseChatModel
    __llm_tools: TooledChatModel

    def __init__(self, invoker: User, messages: list[BaseMessage]):
        super().__init__(config.verbose)
        self.__prompt = SystemMessage(predefined_prompts.chat_telegram)
        self.__messages = []
        self.__messages.append(self.__prompt)
        self.__messages.extend(messages)
        self.__invoker = invoker
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

    def respond(self) -> AIMessage:
        self.sprint(f"Starting chat completion for '{self.__last_message.content}'")
        if isinstance(self.__llm_base, ChatOpenAI):
            if not self.__invoker.open_ai_key:
                self.sprint(f"No API key found for #{self.__invoker.id}")
                # TODO: this should eventually get replaced by a key storing function
                if str(self.__last_message.content).startswith("/open-ai-key"):
                    self.sprint("Attempting to store a new OpenAI API key")
                    self.sprint("  - not implemented yet")
                error_message = MULTI_MESSAGE_DELIMITER.join(
                    [
                        "You need to send your Open AI key first, like so:",
                        "/open-ai-key sk-0123456789ABCDEF",
                        "Note that this feature is not working yet 😬"
                    ]
                )
                return self.__append(AIMessage(error_message))
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
            self.sprint(f"Chat completion failed: {str(e)}")
            return self.__append(AIMessage(f"Oops…\n{str(e)}"))
