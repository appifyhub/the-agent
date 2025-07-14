from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_perplexity import ChatPerplexity

from features.external_tools.external_tool import ExternalToolProvider, ToolType
from features.external_tools.external_tool_provider_library import (
    ANTHROPIC,
    OPEN_AI,
    PERPLEXITY,
)
from features.external_tools.tool_choice_resolver import ConfiguredTool
from util.config import config


def create(configured_tool: ConfiguredTool, for_type: ToolType) -> BaseChatModel:
    tool, api_key = configured_tool
    temperature_percent = __get_temperature_percent(for_type)
    temperature = __normalize_temperature(temperature_percent, tool.provider)
    max_tokens = __get_max_tokens(for_type)
    timeout = __get_timeout(for_type)
    max_retries = config.web_retries

    model_args = {
        "model": tool.id,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "timeout": timeout,
        "max_retries": max_retries,
        "api_key": api_key,
    }

    provider_id = tool.provider.id
    if provider_id == OPEN_AI.id:
        return ChatOpenAI(**model_args)
    elif provider_id == ANTHROPIC.id:
        return ChatAnthropic(**model_args)
    elif provider_id == PERPLEXITY.id:
        return ChatPerplexity(**model_args)
    else:
        raise ValueError(f"{tool.provider.name}/{tool.name} does not support LLMs")


def __get_temperature_percent(tool_type: ToolType) -> float:
    match tool_type:
        case ToolType.chat:
            return 0.25
        case ToolType.reasoning:
            return 0.25
        case ToolType.copywriting:
            return 0.4
        case ToolType.vision:
            return 0.25
        case ToolType.search:
            return 0.35
    raise ValueError(f"{tool_type} does not support temperature")


def __normalize_temperature(temperature_percent: float, provider: ExternalToolProvider) -> float:
    match provider.id:
        case OPEN_AI.id:
            return temperature_percent * 2
        case ANTHROPIC.id:
            return temperature_percent * 1
        case PERPLEXITY.id:
            return temperature_percent * 2
    raise ValueError(f"{provider.name}/{provider.id} does not support temperature")


def __get_max_tokens(tool_type: ToolType) -> int:
    match tool_type:
        case ToolType.chat:
            return 600
        case ToolType.reasoning:
            return 2000
        case ToolType.copywriting:
            return 500
        case ToolType.vision:
            return 2000
        case ToolType.search:
            return 1000
    raise ValueError(f"{tool_type} does not support token limits")


def __get_timeout(tool_type: ToolType) -> float:
    match tool_type:
        case ToolType.chat:
            return float(config.web_timeout_s)
        case ToolType.reasoning:
            return float(config.web_timeout_s) * 3
        case ToolType.copywriting:
            return float(config.web_timeout_s)
        case ToolType.vision:
            return float(config.web_timeout_s) * 2
        case ToolType.search:
            return float(config.web_timeout_s) * 3
    raise ValueError(f"{tool_type} does not support text timeouts")
