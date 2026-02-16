from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_perplexity import ChatPerplexity

from features.external_tools.external_tool import ExternalTool, ExternalToolProvider, ToolType
from features.external_tools.external_tool_provider_library import (
    ANTHROPIC,
    GOOGLE_AI,
    OPEN_AI,
    PERPLEXITY,
)
from features.external_tools.configured_tool import ConfiguredTool
from util.config import config

def create(configured_tool: ConfiguredTool) -> BaseChatModel:
    definition = configured_tool.definition
    purpose = configured_tool.purpose

    model_args = {
        "model": definition.id,
        "temperature": __normalize_temperature(purpose.temperature_percent, definition.provider),
        "max_tokens": purpose.max_output_tokens,
        "timeout": __get_timeout(purpose, definition),
        "max_retries": config.web_retries,
        "api_key": configured_tool.token,
    }

    match definition.provider.id:
        case OPEN_AI.id:
            return ChatOpenAI(**model_args)
        case ANTHROPIC.id:
            return ChatAnthropic(**model_args)
        case PERPLEXITY.id:
            return ChatPerplexity(**model_args)
        case GOOGLE_AI.id:
            return ChatGoogleGenerativeAI(**model_args)
    raise ValueError(f"{definition.provider.name}/{definition.name} does not support LLMs")

def __normalize_temperature(temperature_percent: float, provider: ExternalToolProvider) -> float:
    match provider.id:
        case OPEN_AI.id:
            return temperature_percent * 2
        case ANTHROPIC.id:
            return temperature_percent * 1
        case PERPLEXITY.id:
            return temperature_percent * 2
        case GOOGLE_AI.id:
            return temperature_percent * 2
    raise ValueError(f"{provider.name}/{provider.id} does not support temperature")

def __get_timeout(tool_type: ToolType, tool: ExternalTool) -> float:
    match tool_type:
        case ToolType.chat:
            if ToolType.reasoning in tool.types:
                return float(config.web_timeout_s) * 3
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
