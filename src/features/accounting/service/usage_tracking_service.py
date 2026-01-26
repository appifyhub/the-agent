import re
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
        output_image_sizes: list[str] | None = None,
        input_image_sizes: list[str] | None = None,
        remote_runtime_seconds: float | None = None,
    ) -> UsageRecord:
        has_token_usage = any(t is not None for t in [input_tokens, output_tokens, total_tokens])
        has_image_sizes = bool(output_image_sizes or input_image_sizes)
        if not has_token_usage and not has_image_sizes:
            raise ValueError(
                f"No usage metadata available for image tool {tool.id} - all metrics (tokens, sizes) are None",
            )

        model_cost_credits: float = self.__calculate_image_cost(
            tool.cost_estimate, output_image_sizes, input_image_sizes, input_tokens, output_tokens, total_tokens,
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
            output_image_sizes = output_image_sizes,
            input_image_sizes = input_image_sizes,
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
        output_image_sizes: list[str] | None,
        input_image_sizes: list[str] | None,
        input_tokens: int | None,
        output_tokens: int | None,
        total_tokens: int | None,
    ) -> float:
        # when tokens are present, we calculate cost based on tokens using LLM logic
        # because some image models (like the ones from Google AI) report token usage
        if input_tokens is not None or output_tokens is not None or total_tokens is not None:
            return self.__calculate_llm_cost(cost, input_tokens, output_tokens, search_tokens = None)

        # calculate output image cost
        total_cost = 0.0
        if output_image_sizes:
            for output_image_size in output_image_sizes:
                # remove spaces and clean up variant units to "k"
                normalized: str = re.sub(r"\s+", "", output_image_size.lower()) \
                    .replace("mb", "k").replace("mp", "k").replace("m", "k")

                if normalized == "1k" and cost.output_image_1k:
                    total_cost += float(cost.output_image_1k)
                elif normalized == "2k" and cost.output_image_2k:
                    total_cost += float(cost.output_image_2k)
                elif normalized == "4k" and cost.output_image_4k:
                    total_cost += float(cost.output_image_4k)
                elif cost.output_image_1k:
                    # fallback to 1k if specific size pricing is missing
                    log.w(f"No pricing for output image size '{output_image_size}', using 1K pricing")
                    total_cost += float(cost.output_image_1k)

        # calculate input image cost
        if input_image_sizes:
            for input_image_size in input_image_sizes:
                if input_image_size == "1k" and cost.input_image_1k:
                    total_cost += float(cost.input_image_1k)
                elif input_image_size == "2k" and cost.input_image_2k:
                    total_cost += float(cost.input_image_2k)
                elif input_image_size == "4k" and cost.input_image_4k:
                    total_cost += float(cost.input_image_4k)
                elif input_image_size == "8k" and cost.input_image_8k:
                    total_cost += float(cost.input_image_8k)
                elif input_image_size == "12k" and cost.input_image_12k:
                    total_cost += float(cost.input_image_12k)
                elif cost.input_image_1k:
                    # fallback to 1k if specific size pricing is missing
                    log.w(f"No pricing for input image size '{input_image_size}', using 1K pricing")
                    total_cost += float(cost.input_image_1k)

        if total_cost > 0:
            return total_cost

        raise ValueError(
            f"Cannot calculate cost for image: no token usage and no pricing for sizes "
            f"(output: {output_image_sizes}, input: {input_image_sizes})",
        )
