from typing import Any, Callable, Dict

from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable


class BaseLLMToolBinder:

    _llm_tool_map: Dict[str, Callable]

    def __init__(self, tools_map: Dict[str, Callable] | None = None):
        if tools_map is None:
            tools_map = {}
        self._llm_tool_map = tools_map

    def bind_tools(self, llm_base: BaseChatModel) -> Runnable[LanguageModelInput, BaseMessage]:
        return llm_base.bind_tools(list(self._llm_tool_map.values()))

    def invoke(self, tool_name: str, args: object) -> str | None:
        selected_tool: Callable[..., Any] | None = self._llm_tool_map.get(tool_name)
        # noinspection PyUnresolvedReferences
        return selected_tool.invoke(args) if (selected_tool is not None) else None

    @property
    def tool_names(self) -> list[str]:
        return list(self._llm_tool_map.keys())
