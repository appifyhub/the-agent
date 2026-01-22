from time import time
from typing import Any, Sequence

from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import Runnable, RunnableConfig

from features.accounting.llm_usage_stats import LLMUsageStats
from features.accounting.usage_tracking_service import UsageTrackingService
from features.external_tools.external_tool import ExternalTool, ToolType


class RunnableUsageTrackingDecorator(Runnable[LanguageModelInput, AIMessage]):
    """We use this when binding LLM tools to return a Runnable others can call."""

    __wrapped_runnable: Runnable[LanguageModelInput, AIMessage]
    __tracking_service: UsageTrackingService
    __external_tool: ExternalTool
    __tool_purpose: ToolType

    def __init__(
        self,
        wrapped_runnable: Runnable[LanguageModelInput, AIMessage],
        tracking_service: UsageTrackingService,
        external_tool: ExternalTool,
        tool_purpose: ToolType,
    ):
        super().__init__()
        self.__wrapped_runnable = wrapped_runnable
        self.__tracking_service = tracking_service
        self.__external_tool = external_tool
        self.__tool_purpose = tool_purpose

    def invoke(self, input: LanguageModelInput, config: RunnableConfig | None = None, **kwargs) -> AIMessage:
        start_time = time()
        response = self.__wrapped_runnable.invoke(input, config, **kwargs)
        runtime_seconds = time() - start_time
        self.__log_usage(response, runtime_seconds)
        return response

    def __log_usage(self, response: BaseMessage, runtime_seconds: float) -> None:
        llm_usage_stats = LLMUsageStats.from_response(response)

        self.__tracking_service.track_text_model(
            tool = self.__external_tool,
            tool_purpose = self.__tool_purpose,
            runtime_seconds = runtime_seconds,
            input_tokens = llm_usage_stats.input_tokens,
            output_tokens = llm_usage_stats.output_tokens,
            search_tokens = llm_usage_stats.search_tokens,
            total_tokens = llm_usage_stats.total_tokens,
        )


class ChatModelUsageTrackingDecorator:

    __wrapped_model: BaseChatModel
    __tracking_service: UsageTrackingService
    __external_tool: ExternalTool
    __tool_purpose: ToolType

    def __init__(
        self,
        wrapped_model: BaseChatModel,
        tracking_service: UsageTrackingService,
        external_tool: ExternalTool,
        tool_purpose: ToolType,
    ):
        self.__wrapped_model = wrapped_model
        self.__tracking_service = tracking_service
        self.__external_tool = external_tool
        self.__tool_purpose = tool_purpose

    def invoke(self, input: LanguageModelInput, config: RunnableConfig | None = None, **kwargs) -> AIMessage:
        start_time = time()
        response = self.__wrapped_model.invoke(input, config, **kwargs)
        runtime_seconds = time() - start_time
        self.__log_usage(response, runtime_seconds)
        return response

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> Runnable[LanguageModelInput, AIMessage]:
        wrapped_runnable = self.__wrapped_model.bind_tools(tools, **kwargs)
        return RunnableUsageTrackingDecorator(
            wrapped_runnable, self.__tracking_service, self.__external_tool, self.__tool_purpose,
        )

    def _generate(self, *args: Any, **kwargs: Any) -> Any:
        return self.__wrapped_model._generate(*args, **kwargs)

    @property
    def _llm_type(self) -> str:
        return self.__wrapped_model._llm_type

    def __log_usage(self, response: BaseMessage, runtime_seconds: float) -> None:
        llm_usage_stats = LLMUsageStats.from_response(response)

        self.__tracking_service.track_text_model(
            tool = self.__external_tool,
            tool_purpose = self.__tool_purpose,
            runtime_seconds = runtime_seconds,
            input_tokens = llm_usage_stats.input_tokens,
            output_tokens = llm_usage_stats.output_tokens,
            search_tokens = llm_usage_stats.search_tokens,
            total_tokens = llm_usage_stats.total_tokens,
        )
