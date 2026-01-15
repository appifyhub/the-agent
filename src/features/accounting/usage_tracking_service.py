from datetime import datetime, timezone

from di.di import DI
from features.accounting.usage_record import UsageRecord
from features.external_tools.external_tool import CostEstimate, ExternalTool
from util import log
from util.config import config


class UsageTrackingService:

    __di: DI

    def __init__(self, di: DI):
        self.__di = di

    def track_llm(
        self,
        tool: ExternalTool,
        runtime_seconds: int,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        search_tokens: int | None = None,
        total_tokens: int | None = None,
    ) -> UsageRecord:
        if all(t is None for t in [input_tokens, output_tokens, search_tokens, total_tokens]):
            raise ValueError(
                f"No usage metadata available for LLM {tool.id} - "
                "all token fields are None",
            )
        # we use provider's total_tokens if available, otherwise calculate from components
        if total_tokens is None:
            total_tokens = (input_tokens or 0) + (output_tokens or 0) + (search_tokens or 0)
        model_cost_credits = self.__calculate_llm_cost(
            tool.cost_estimate,
            input_tokens, output_tokens, search_tokens,
        )
        record = UsageRecord(
            user_id = self.__di.invoker.id,
            chat_id = self.__di.require_invoker_chat().chat_id,
            tool = tool,
            timestamp = datetime.now(timezone.utc),
            model_cost_credits = model_cost_credits,
            maintenance_fee_credits = config.usage_maintenance_fee_credits,
            total_cost_credits = model_cost_credits + config.usage_maintenance_fee_credits,
            runtime_seconds = runtime_seconds,
            input_tokens = input_tokens,
            output_tokens = output_tokens,
            total_tokens = total_tokens,
            search_tokens = search_tokens,
        )
        log.d("LLM Usage Tracked", record)
        return record

    def track_image(
        self,
        tool: ExternalTool,
        runtime_seconds: int,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        total_tokens: int | None = None,
        image_count: int = 1,
        image_size: str | None = None,
    ) -> UsageRecord:
        if all(t is None for t in [input_tokens, output_tokens, total_tokens, image_size]):
            raise ValueError(
                f"No usage metadata available for image tool {tool.id} - "
                "all metrics (tokens, size) are None",
            )
        # we use provider's total_tokens if available, otherwise calculate from components
        if total_tokens is None:
            total_tokens = (input_tokens or 0) + (output_tokens or 0)
        model_cost_credits = self.__calculate_image_cost(
            tool.cost_estimate, image_size,
            input_tokens, output_tokens, total_tokens,
        )
        record = UsageRecord(
            user_id = self.__di.invoker.id,
            chat_id = self.__di.require_invoker_chat().chat_id,
            tool = tool,
            timestamp = datetime.now(timezone.utc),
            model_cost_credits = model_cost_credits,
            maintenance_fee_credits = config.usage_maintenance_fee_credits,
            total_cost_credits = model_cost_credits + config.usage_maintenance_fee_credits,
            runtime_seconds = runtime_seconds,
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
        runtime_seconds: int,
    ) -> UsageRecord:
        model_cost_credits = self.__calculate_api_cost(tool.cost_estimate)
        record = UsageRecord(
            user_id = self.__di.invoker.id,
            chat_id = self.__di.require_invoker_chat().chat_id,
            tool = tool,
            timestamp = datetime.now(timezone.utc),
            model_cost_credits = model_cost_credits,
            maintenance_fee_credits = config.usage_maintenance_fee_credits,
            total_cost_credits = model_cost_credits + config.usage_maintenance_fee_credits,
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
        if input_tokens and cost.input_1m_tokens:
            result += (input_tokens / 1_000_000) * cost.input_1m_tokens
        if output_tokens and cost.output_1m_tokens:
            result += (output_tokens / 1_000_000) * cost.output_1m_tokens
        # search tokens cost is always added for some models (kind of like a separate API fee)
        if search_tokens and cost.search_1m_tokens:
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
        # some image models (like the ones from Google AI) report token usage
        if input_tokens or output_tokens or total_tokens:
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

    def __calculate_api_cost(self, estimate: CostEstimate) -> float:
        return float(estimate.api_single_call or 0)
