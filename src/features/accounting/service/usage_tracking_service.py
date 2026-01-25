from datetime import datetime, timezone

from di.di import DI
from features.accounting.stats.usage_record import UsageRecord
from features.external_tools.external_tool import CostEstimate, ExternalTool, ToolType
from util import log
from util.config import config


class UsageTrackingService:

    __di: DI

    def __init__(self, di: DI):
        self.__di = di

    def track_text_model(
        self,
        tool: ExternalTool,
        tool_purpose: ToolType,
        runtime_seconds: float,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        search_tokens: int | None = None,
        total_tokens: int | None = None,
        remote_runtime_seconds: float | None = None,
    ) -> UsageRecord:
        # ensure that we have at least some usage metadata
        has_token_usage = any(t is not None for t in [input_tokens, output_tokens, search_tokens, total_tokens])
        has_duration_usage = remote_runtime_seconds is not None
        if not has_token_usage and not has_duration_usage:
            raise ValueError(
                f"No usage metadata available for LLM {tool.id} - all token and duration fields are None",
            )

        model_cost_credits: float = self.__calculate_llm_cost(tool.cost_estimate, input_tokens, output_tokens, search_tokens)
        remote_runtime_cost_credits: float = (tool.cost_estimate.second_of_runtime or 0) \
            * (remote_runtime_seconds or runtime_seconds)
        api_cost_credits: float = float(tool.cost_estimate.api_call or 0)
        maintenance_fee_credits: float = config.usage_maintenance_fee_credits
        total_cost_credits: float = model_cost_credits + api_cost_credits + remote_runtime_cost_credits + maintenance_fee_credits

        record = UsageRecord(
            user_id = self.__di.invoker.id,
            chat_id = self.__di.invoker_chat.chat_id if self.__di.invoker_chat else None,
            tool = tool,
            tool_purpose = tool_purpose,
            timestamp = datetime.now(timezone.utc),
            model_cost_credits = model_cost_credits,
            api_call_cost_credits = api_cost_credits,
            remote_runtime_cost_credits = remote_runtime_cost_credits,
            maintenance_fee_credits = maintenance_fee_credits,
            total_cost_credits = total_cost_credits,
            runtime_seconds = runtime_seconds,
            remote_runtime_seconds = remote_runtime_seconds,
            input_tokens = input_tokens,
            output_tokens = output_tokens,
            total_tokens = total_tokens,
            search_tokens = search_tokens,
        )
        log.d("LLM Usage Tracked", record)
        return record

    def track_image_model(
        self,
        tool: ExternalTool,
        tool_purpose: ToolType,
        runtime_seconds: float,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        total_tokens: int | None = None,
        image_count: int = 1,
        image_size: str | None = None,
        remote_runtime_seconds: float | None = None,
    ) -> UsageRecord:
        if all(t is None for t in [input_tokens, output_tokens, total_tokens, image_size]):
            raise ValueError(
                f"No usage metadata available for image tool {tool.id} - all metrics (tokens, size) are None",
            )

        model_cost_credits: float = self.__calculate_image_cost(
            tool.cost_estimate, image_size, input_tokens, output_tokens, total_tokens,
        )
        api_cost_credits: float = float(tool.cost_estimate.api_call or 0)
        remote_runtime_cost_credits: float = (tool.cost_estimate.second_of_runtime or 0) \
            * (remote_runtime_seconds or runtime_seconds)
        maintenance_fee_credits: float = config.usage_maintenance_fee_credits
        total_cost_credits: float = model_cost_credits + api_cost_credits + remote_runtime_cost_credits + maintenance_fee_credits

        record = UsageRecord(
            user_id = self.__di.invoker.id,
            chat_id = self.__di.invoker_chat.chat_id if self.__di.invoker_chat else None,
            tool = tool,
            tool_purpose = tool_purpose,
            timestamp = datetime.now(timezone.utc),
            model_cost_credits = model_cost_credits,
            remote_runtime_cost_credits = remote_runtime_cost_credits,
            api_call_cost_credits = api_cost_credits,
            maintenance_fee_credits = maintenance_fee_credits,
            total_cost_credits = total_cost_credits,
            runtime_seconds = runtime_seconds,
            remote_runtime_seconds = remote_runtime_seconds,
            input_tokens = input_tokens,
            output_tokens = output_tokens,
            total_tokens = total_tokens,
            image_count = image_count,
            image_size = image_size,
        )
        log.d("Image Usage Tracked", record)
        return record

    def track_api_call(
        self,
        tool: ExternalTool,
        tool_purpose: ToolType,
        runtime_seconds: float,
    ) -> UsageRecord:
        api_call_cost: float = float(tool.cost_estimate.api_call or 0)
        remote_runtime_cost_credits: float = (tool.cost_estimate.second_of_runtime or 0) * runtime_seconds
        maintenance_fee_credits: float = config.usage_maintenance_fee_credits
        total_cost_credits: float = api_call_cost + remote_runtime_cost_credits + maintenance_fee_credits

        record = UsageRecord(
            user_id = self.__di.invoker.id,
            chat_id = self.__di.invoker_chat.chat_id if self.__di.invoker_chat else None,
            tool = tool,
            tool_purpose = tool_purpose,
            timestamp = datetime.now(timezone.utc),
            model_cost_credits = 0.0,
            remote_runtime_cost_credits = remote_runtime_cost_credits,
            api_call_cost_credits = api_call_cost,
            maintenance_fee_credits = maintenance_fee_credits,
            total_cost_credits = total_cost_credits,
            runtime_seconds = runtime_seconds,
        )
        log.d("API Call Tracked", record)
        return record

    def __calculate_llm_cost(
        self,
        cost: CostEstimate,
        input_tokens: int | None,
        output_tokens: int | None,
        search_tokens: int | None,
    ) -> float:
        result = 0.0
        if input_tokens is not None and cost.input_1m_tokens is not None:
            result += (input_tokens / 1_000_000) * cost.input_1m_tokens
        if output_tokens is not None and cost.output_1m_tokens is not None:
            result += (output_tokens / 1_000_000) * cost.output_1m_tokens
        if search_tokens is not None and cost.search_1m_tokens is not None:
            result += (search_tokens / 1_000_000) * cost.search_1m_tokens
        return result

    def __calculate_image_cost(
        self,
        cost: CostEstimate,
        image_size: str | None,
        input_tokens: int | None,
        output_tokens: int | None,
        total_tokens: int | None,
    ) -> float:
        # when tokens are present, we calculate cost based on tokens using LLM logic
        # because some image models (like the ones from Google AI) report token usage
        if input_tokens is not None or output_tokens is not None or total_tokens is not None:
            return self.__calculate_llm_cost(cost, input_tokens, output_tokens, search_tokens = None)

        image_size_lower = image_size.lower().strip() if image_size else None
        if image_size_lower == "1k" and cost.image_1k:
            return float(cost.image_1k)
        if image_size_lower == "2k" and cost.image_2k:
            return float(cost.image_2k)
        if image_size_lower == "4k" and cost.image_4k:
            return float(cost.image_4k)

        # fallback to 1k if specific size pricing is missing (and image_size was provided)
        if image_size and cost.image_1k:
            log.w(f"No pricing for image size '{image_size}', using 1K pricing")
            return float(cost.image_1k)

        raise ValueError(
            f"Cannot calculate cost for image: no token usage and no pricing for size '{image_size}'",
        )
