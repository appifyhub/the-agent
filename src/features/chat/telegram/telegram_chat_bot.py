import random
import re
from typing import Any, Tuple, TypeVar

from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from db.schema.chat_config import ChatConfig
from db.schema.user import User
from features.chat.command_processor import CommandProcessor
from features.chat.telegram.telegram_progress_notifier import TelegramProgressNotifier
from features.chat.tools.tools_library import ToolsLibrary
from features.external_tools.access_token_resolver import AccessTokenResolver
from features.external_tools.external_tool_library import GPT_4_1_MINI
from features.prompting import prompt_library
from features.prompting.prompt_library import TELEGRAM_BOT_USER
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

TMessage = TypeVar("TMessage", bound = BaseMessage)  # Generic message type
TooledChatModel = Runnable[LanguageModelInput, BaseMessage]


class TelegramChatBot(SafePrinterMixin):
    __chat: ChatConfig
    __invoker: User
    __tools_library: ToolsLibrary
    __messages: list[BaseMessage]
    __attachment_ids: list[str]
    __raw_last_message: str  # excludes the resolver formatting
    __command_processor: CommandProcessor
    __progress_notifier: TelegramProgressNotifier
    __access_token_resolver: AccessTokenResolver
    __llm_has_access_token: bool
    __llm_base: BaseChatModel
    __llm_tools: TooledChatModel

    def __init__(
        self,
        chat: ChatConfig,
        invoker: User,
        messages: list[BaseMessage],
        attachment_ids: list[str],
        raw_last_message: str,
        command_processor: CommandProcessor,
        progress_notifier: TelegramProgressNotifier,
        access_token_resolver: AccessTokenResolver,
    ):
        super().__init__(config.verbose)
        self.__chat = chat
        self.__invoker = invoker
        self.__tools_library = ToolsLibrary()
        self.__messages = []
        self.__messages.append(
            SystemMessage(
                prompt_library.add_metadata(
                    base_prompt = prompt_library.translator_on_response(
                        base_prompt = prompt_library.chat_telegram,
                        language_name = chat.language_name,
                        language_iso_code = chat.language_iso_code,
                    ),
                    author = invoker,
                    chat_id = chat.chat_id,
                    chat_title = chat.title,
                    available_tools = self.__tools_library.tool_names,
                ),
            ),
        )
        self.__messages.extend(messages)
        self.__attachment_ids = attachment_ids
        self.__raw_last_message = raw_last_message
        self.__command_processor = command_processor
        self.__progress_notifier = progress_notifier
        self.__access_token_resolver = access_token_resolver

        access_token = self.__access_token_resolver.get_access_token_for_tool(GPT_4_1_MINI)
        self.__llm_has_access_token = access_token is not None
        self.__llm_base = ChatOpenAI(
            model = GPT_4_1_MINI.id,
            temperature = 0.5,
            max_tokens = 600,
            timeout = float(config.web_timeout_s),
            max_retries = config.web_retries,
            api_key = access_token or SecretStr(str(None)),
        )
        self.__llm_tools = self.__tools_library.bind_tools(self.__llm_base)

    def __add_message(self, message: TMessage) -> TMessage:
        self.__messages.append(message)
        return message

    @property
    def __last_message(self) -> BaseMessage:
        return self.__messages[-1]

    def execute(self) -> AIMessage | None:
        self.sprint(f"Starting chat completion for '{self.__last_message.content}'")

        # check if a reply is needed at all
        if not self.should_reply():
            return None

        # handle commands first
        answer, status = self.process_commands()
        if status == CommandProcessor.Result.success:
            # command was processed successfully, no reply is needed
            return None
        if status == CommandProcessor.Result.failed:
            # command was not processed successfully, reply with the error
            return answer

        # not a known command, but also no API key found
        if not self.__llm_has_access_token:
            self.sprint(f"No API key found for #{self.__invoker.id.hex}, skipping LLM processing")
            answer = AIMessage(prompt_library.error_general_problem("Not configured."))
            return answer

        # main flow: process the messages using LLM AI
        try:
            iteration = 1
            self.__progress_notifier.start()
            while True:
                # don't blow up the costs
                if iteration > config.max_chatbot_iterations:
                    message = f"Reached max iterations ({config.max_chatbot_iterations}), finishing"
                    self.sprint(message)
                    raise OverflowError(message)

                # run the actual LLM completion
                llm_answer = self.__llm_tools.invoke(self.__messages)
                answer = self.__add_message(llm_answer)

                # noinspection Pydantic
                if not answer.tool_calls:
                    self.sprint(f"Iteration #{iteration} has no tool calls.")
                    if not isinstance(answer, AIMessage):
                        raise AssertionError(f"Received a non-AI message from LLM: {answer}")
                    system_correction_added = False
                    for attachment_id in self.__attachment_ids:
                        clean_attachment_id = re.sub(r"[ _-]", "", attachment_id)
                        truncated_attachment_id = attachment_id[-10:]
                        if (
                            attachment_id in str(answer.content)
                            or clean_attachment_id in str(answer.content)
                            or truncated_attachment_id in str(answer.content)
                        ):
                            self.sprint("Found approximate attachment ID in the answer, adding system correction")
                            system_correction = SystemMessage(
                                "Error: Attachment IDs should never be sent to users. "
                                "You probably meant to call a tool. "
                                "When calling tools, make sure to call the tools using verbatim attachment IDs, "
                                "without any truncation, cleaning, or formatting. "
                                "Please use the tools to process attachments instead. "
                                "Disregard this instruction for the remainder of the conversation. ",
                            )
                            self.__add_message(system_correction)
                            system_correction_added = True
                            break
                    if system_correction_added:
                        iteration += 1
                        continue
                    self.sprint(f"Finishing with {type(answer)}: {len(answer.content)} characters")
                    return answer

                self.sprint(f"Iteration #{iteration} has tool calls, processing...")
                iteration += 1

                # noinspection Pydantic
                for tool_call in answer.tool_calls:
                    tool_id: Any = tool_call["id"]
                    tool_name: Any = tool_call["name"]
                    tool_args: Any = tool_call["args"]

                    self.sprint(f"  Processing {tool_id} / '{tool_name}' tool call")
                    tool_result: str | None = self.__tools_library.invoke(tool_name, tool_args)
                    if not tool_result:
                        self.sprint(f"Tool {tool_name} not invoked!")
                        continue
                    self.__add_message(ToolMessage(tool_result, tool_call_id = tool_id))

                if not isinstance(self.__last_message, ToolMessage):
                    raise LookupError("Couldn't find tools to invoke!")
        except Exception as e:
            self.sprint("Chat completion failed", e)
            text = prompt_library.error_general_problem(str(e))
            return AIMessage(text)
        finally:
            self.__progress_notifier.stop()

    def process_commands(self) -> Tuple[AIMessage, CommandProcessor.Result]:
        result = self.__command_processor.execute(self.__raw_last_message)
        self.sprint(f"Command processing result is {result.value}")
        if result == CommandProcessor.Result.unknown or result == CommandProcessor.Result.success:
            text = ""
        elif result == CommandProcessor.Result.failed:
            text = prompt_library.error_general_problem("Unknown command.")
        else:
            raise NotImplementedError("Wild branch")
        return AIMessage(text), result

    def should_reply(self) -> bool:
        has_content = bool(self.__raw_last_message.strip())
        is_not_recursive = self.__invoker.telegram_username != TELEGRAM_BOT_USER.telegram_username
        is_bot_mentioned = f"@{TELEGRAM_BOT_USER.telegram_username}" in self.__raw_last_message
        if self.__chat.reply_chance_percent == 100:
            should_reply_at_random = True
        elif self.__chat.reply_chance_percent == 0:
            should_reply_at_random = False
        else:
            should_reply_at_random = random.randint(0, 100) <= self.__chat.reply_chance_percent
        should_reply = (
            has_content and
            is_not_recursive and
            (self.__chat.is_private or is_bot_mentioned or should_reply_at_random)
        )
        self.sprint(
            f"Reply decision: {"REPLYING" if should_reply else "NOT REPLYING"}. Conditions:\n"
            f"  · has_content      = {has_content}\n"
            f"  · is_not_recursive = {is_not_recursive}\n"
            f"  · is_private_chat  = {self.__chat.is_private}\n"
            f"  · is_bot_mentioned = {is_bot_mentioned}\n"
            f"  · reply_at_random  = {should_reply_at_random}\n"
            f"  · reply_chance     = {self.__chat.reply_chance_percent}%",
        )
        return should_reply
