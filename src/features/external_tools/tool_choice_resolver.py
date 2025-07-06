from features.external_tools.external_tool import ExternalTool, ExternalToolProvider, ToolType
from features.external_tools.external_tool_library import ALL_EXTERNAL_TOOLS
from features.external_tools.external_tool_provider_library import ALL_PROVIDERS

ToolsByProvider = dict[ExternalToolProvider, list[ExternalTool]]


class ToolChoiceResolver:
    @staticmethod
    def find_tool_by_id(tool_id: str) -> ExternalTool | None:
        for tool in ALL_EXTERNAL_TOOLS:
            if tool.id == tool_id:
                return tool
        return None

    @staticmethod
    def get_eligible_tools_by_provider(
        tool_type: ToolType,
        preferred_tool: str | ExternalTool | None = None,
    ) -> ToolsByProvider:
        eligible_tools = [tool for tool in ALL_EXTERNAL_TOOLS if tool_type in tool.types]
        provider_tools: ToolsByProvider = {provider: [] for provider in ALL_PROVIDERS}
        for tool in eligible_tools:
            provider_tools[tool.provider].append(tool)

        resolved_preferred_tool: ExternalTool | None = (
            ToolChoiceResolver.find_tool_by_id(preferred_tool) if isinstance(preferred_tool, str) else preferred_tool
        )

        # no preferred tools, we won't change the tool ordering
        if not resolved_preferred_tool or tool_type not in resolved_preferred_tool.types:
            return provider_tools

        # move the preferred tool to the front of its provider's list
        provider_tool_list = provider_tools[resolved_preferred_tool.provider]
        provider_tool_list = [tool for tool in provider_tool_list if tool.id != resolved_preferred_tool.id]
        provider_tools[resolved_preferred_tool.provider] = [resolved_preferred_tool] + provider_tool_list

        return provider_tools
