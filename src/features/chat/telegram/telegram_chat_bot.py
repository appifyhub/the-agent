import random
import re
from typing import Any, Tuple, TypeVar

from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_core.runnables import Runnable

from di.di import DI
from features.chat.command_processor import CommandProcessor
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import GPT_4_1_MINI
from features.external_tools.tool_choice_resolver import ConfiguredTool
from features.prompting import prompt_library
from features.prompting.prompt_library import TELEGRAM_BOT_USER
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

TMessage = TypeVar("TMessage", bound = BaseMessage)  # Generic message type
TooledChatModel = Runnable[LanguageModelInput, BaseMessage]


class TelegramChatBot(SafePrinterMixin):
    DEFAULT_TOOL: ExternalTool = GPT_4_1_MINI
    TOOL_TYPE: ToolType = ToolType.chat

    __messages: list[BaseMessage]
    __raw_last_message: str  # excludes the resolver formatting
    __last_message_id: str
    __attachment_ids: list[str]
    __configured_tool: ConfiguredTool | None
    __di: DI

    def __init__(
        self,
        messages: list[BaseMessage],
        raw_last_message: str,
        last_message_id: str,
        attachment_ids: list[str],
        configured_tool: ConfiguredTool | None,
        di: DI,
    ):
        super().__init__(config.verbose)
        self.__messages = []
        self.__messages.append(
            SystemMessage(
                prompt_library.add_metadata(
                    base_prompt = prompt_library.translator_on_response(
                        base_prompt = prompt_library.chat_telegram,
                        language_name = di.invoker_chat.language_name,
                        language_iso_code = di.invoker_chat.language_iso_code,
                    ),
                    author = di.invoker,
                    chat_id = di.invoker_chat.chat_id,
                    chat_title = di.invoker_chat.title,
                    available_tools = di.llm_tool_library.tool_names,
                ),
            ),
        )
        self.__messages.extend(messages)
        self.__raw_last_message = raw_last_message
        self.__last_message_id = last_message_id
        self.__attachment_ids = attachment_ids
        self.__configured_tool = configured_tool
        self.__di = di

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
        if not self.__configured_tool:
            self.sprint(f"No API key found for #{self.__di.invoker.id.hex}, skipping LLM processing")
            answer = AIMessage(prompt_library.error_general_problem("Not configured."))
            return answer

        # prepare the LLM model and connected tools
        progress_notifier = self.__di.telegram_progress_notifier(self.__last_message_id)
        base_model = self.__di.chat_langchain_model(self.__configured_tool)
        tools_model: TooledChatModel | None = None
        try:
            tools_model = self.__di.llm_tool_library.bind_tools(base_model)
        except Exception as e:
            self.sprint("Failed to bind tools to the LLM model, using base model", e)

        # main flow: process the messages using the LLM
        try:
            iteration = 1
            progress_notifier.start()
            while True:
                # don't blow up the costs
                if iteration > config.max_chatbot_iterations:
                    message = f"Reached max iterations ({config.max_chatbot_iterations}), finishing"
                    self.sprint(message)
                    raise OverflowError(message)

                # run the actual LLM completion
                llm_answer = (tools_model or base_model).invoke(self.__messages)
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
                    self.sprint(f"Finishing chat response with {len(answer.content)} characters")
                    return answer

                self.sprint(f"Iteration #{iteration} has tool calls, processing...")
                iteration += 1

                # noinspection Pydantic
                for tool_call in answer.tool_calls:
                    tool_id: Any = tool_call["id"]
                    tool_name: Any = tool_call["name"]
                    tool_args: Any = tool_call["args"]

                    self.sprint(f"  Processing {tool_id} / '{tool_name}' tool call")
                    tool_result: str | None = self.__di.llm_tool_library.invoke(tool_name, tool_args)
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
            progress_notifier.stop()

    def process_commands(self) -> Tuple[AIMessage, CommandProcessor.Result]:
        result = self.__di.command_processor.execute(self.__raw_last_message)
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
        is_not_recursive = self.__di.invoker.telegram_username != TELEGRAM_BOT_USER.telegram_username
        is_bot_mentioned = f"@{TELEGRAM_BOT_USER.telegram_username}" in self.__raw_last_message
        if self.__di.invoker_chat.reply_chance_percent == 100:
            should_reply_at_random = True
        elif self.__di.invoker_chat.reply_chance_percent == 0:
            should_reply_at_random = False
        else:
            should_reply_at_random = random.randint(0, 100) <= self.__di.invoker_chat.reply_chance_percent
        should_reply = (
            has_content and
            is_not_recursive and
            (self.__di.invoker_chat.is_private or is_bot_mentioned or should_reply_at_random)
        )
        self.sprint(
            f"Reply decision: {'REPLYING' if should_reply else 'NOT REPLYING'}. Conditions:\n"
            f"  · has_content      = {has_content}\n"
            f"  · is_not_recursive = {is_not_recursive}\n"
            f"  · is_private_chat  = {self.__di.invoker_chat.is_private}\n"
            f"  · is_bot_mentioned = {is_bot_mentioned}\n"
            f"  · reply_at_random  = {should_reply_at_random}\n"
            f"  · reply_chance     = {self.__di.invoker_chat.reply_chance_percent}%",
        )
        return should_reply
