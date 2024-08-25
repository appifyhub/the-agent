from typing import Dict, Callable, Any

from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable


class BaseToolBinder:
    _tools_map: Dict[str, Callable]

    def __init__(self, tools_map: Dict[str, Callable] | None = None):
        if tools_map is None:
            tools_map = {}
        self._tools_map = tools_map

    def bind_tools(self, llm_base: BaseChatModel) -> Runnable[LanguageModelInput, BaseMessage]:
        return llm_base.bind_tools(list(self._tools_map.values()))

    def invoke(self, tool_name: str, args: object) -> str | None:
        selected_tool: Callable[..., Any] | None = self._tools_map.get(tool_name)
        # noinspection PyUnresolvedReferences
        return selected_tool.invoke(args) if (selected_tool is not None) else None
