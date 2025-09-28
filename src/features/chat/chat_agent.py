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
from features.integrations import prompt_resolvers
from features.integrations.integrations import resolve_agent_user, resolve_external_handle
from util import log
from util.config import config

TMessage = TypeVar("TMessage", bound = BaseMessage)  # Generic message type
TooledChatModel = Runnable[LanguageModelInput, BaseMessage]


class ChatAgent:

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
        system_prompt = prompt_resolvers.chat(di.invoker, di.require_invoker_chat(), str(di.llm_tool_library.tool_names))
        self.__messages = []
        self.__messages.append(SystemMessage(system_prompt))
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
        log.t(f"Starting chat completion for '{self.__last_message.content}'")

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
            log.w(f"No API key found for #{self.__di.invoker.id.hex}, skipping LLM processing")
            message = prompt_resolvers.simple_chat_error("Not configured.")
            answer = AIMessage(message)
            return answer

        # prepare the LLM model and connected tools
        progress_notifier = self.__di.telegram_progress_notifier(self.__last_message_id)  # TODO: not just Telegram
        base_model = self.__di.chat_langchain_model(self.__configured_tool)
        tools_model: None | TooledChatModel = None
        try:
            tools_model = self.__di.llm_tool_library.bind_tools(base_model)
        except Exception as e:
            log.w("Failed to bind tools to the LLM model, using base model", e)

        # main flow: process the messages using the LLM
        try:
            iteration = 1
            progress_notifier.start()
            while True:
                # don't blow up the costs
                if iteration > config.max_chatbot_iterations:
                    raise OverflowError(log.e(f"Reached max iterations ({config.max_chatbot_iterations}), finishing"))

                # run the actual LLM completion
                llm_answer = (tools_model or base_model).invoke(self.__messages)
                answer = self.__add_message(llm_answer)

                # noinspection Pydantic
                if not answer.tool_calls:  # type: ignore
                    log.d(f"Iteration #{iteration} has no tool calls.")
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
                            log.w("Found approximate attachment ID in the answer, adding system correction")
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
                    log.i(f"Finishing chat response with {len(answer.content)} characters")
                    return answer

                log.d(f"Iteration #{iteration} has tool calls, processing...")
                iteration += 1

                # noinspection Pydantic
                for tool_call in answer.tool_calls:  # type: ignore
                    tool_id: Any = tool_call["id"]
                    tool_name: Any = tool_call["name"]
                    tool_args: Any = tool_call["args"]

                    log.t(f"  Processing {tool_id} / '{tool_name}' tool call")
                    tool_result: str | None = self.__di.llm_tool_library.invoke(tool_name, tool_args)
                    if not tool_result:
                        log.w(f"Tool {tool_name} not invoked!")
                        continue
                    self.__add_message(ToolMessage(tool_result, tool_call_id = tool_id))

                if not isinstance(self.__last_message, ToolMessage):
                    raise LookupError("Couldn't find tools to invoke!")
        except Exception as e:
            log.e("Chat completion failed", e)
            message = prompt_resolvers.simple_chat_error(str(e))
            return AIMessage(message)
        finally:
            progress_notifier.stop()

    def process_commands(self) -> Tuple[AIMessage, CommandProcessor.Result]:
        result = self.__di.command_processor.execute(self.__raw_last_message)
        log.d(f"Command processing result is {result.value}")
        # noinspection PyUnreachableCode
        if result == CommandProcessor.Result.unknown or result == CommandProcessor.Result.success:
            message = ""
        elif result == CommandProcessor.Result.failed:
            message = prompt_resolvers.simple_chat_error("Unknown command.")
        else:
            raise NotImplementedError("Wild branch")
        return AIMessage(message), result

    def should_reply(self) -> bool:
        has_content = bool(self.__raw_last_message.strip())
        chat_type = self.__di.require_invoker_chat_type()
        agent_user = resolve_agent_user(chat_type)
        invoker_handle = resolve_external_handle(self.__di.invoker, chat_type)
        agent_handle = resolve_external_handle(agent_user, chat_type)
        is_not_recursive = invoker_handle != agent_handle
        is_bot_mentioned = f"@{agent_handle}" in self.__raw_last_message
        invoker_chat = self.__di.require_invoker_chat()
        if invoker_chat.reply_chance_percent == 100:
            should_reply_at_random = True
        elif invoker_chat.reply_chance_percent == 0:
            should_reply_at_random = False
        else:
            should_reply_at_random = random.randint(0, 100) <= invoker_chat.reply_chance_percent
        should_reply = (
            has_content and
            is_not_recursive and
            (invoker_chat.is_private or is_bot_mentioned or should_reply_at_random)
        )
        log.d(
            f"Reply decision: {'REPLYING' if should_reply else 'NOT REPLYING'}. Conditions:\n"
            f"  · has_content      = {has_content}\n"
            f"  · is_not_recursive = {is_not_recursive}\n"
            f"  · is_private_chat  = {invoker_chat.is_private}\n"
            f"  · is_bot_mentioned = {is_bot_mentioned}\n"
            f"  · reply_at_random  = {should_reply_at_random}\n"
            f"  · reply_chance     = {invoker_chat.reply_chance_percent}%",
        )
        return should_reply
