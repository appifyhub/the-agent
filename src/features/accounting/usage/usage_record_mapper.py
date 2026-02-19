from db.model.usage_record import UsageRecordDB
from features.accounting.usage.usage_record import UsageRecord
from features.external_tools.external_tool import ExternalTool, ExternalToolProvider, ToolType
from features.external_tools.external_tool_library import ALL_EXTERNAL_TOOLS
from util import log


def domain(db_model: UsageRecordDB | None) -> UsageRecord | None:
    if db_model is None:
        return None

    # try to find the tool among existing tools
    tool: ExternalTool | None = None
    for ext_tool in ALL_EXTERNAL_TOOLS:
        if ext_tool.id == db_model.tool_id:
            tool = ext_tool
            break

    # if tool is not found, create a new dummy tool
    tool_purpose: ToolType = ToolType.deprecated
    if tool is None:
        tool = ExternalTool(
            id = db_model.tool_id,
            name = db_model.tool_name,
            provider = ExternalToolProvider(
                id = db_model.provider_id,
                name = db_model.provider_name,
                token_management_url = "",
                token_format = "",
                tools = [],
            ),
            types = [],
            cost_estimate = None,
        )
    else:
        try:
            tool_purpose = ToolType(db_model.purpose)
        except ValueError:
            log.d("Parsed a deprecated purpose", db_model.purpose)
            tool_purpose = ToolType.deprecated

    return UsageRecord(
        user_id = db_model.user_id,
        payer_id = db_model.payer_id,
        uses_credits = db_model.uses_credits,
        is_failed = db_model.is_failed,
        chat_id = db_model.chat_id,
        tool = tool,
        tool_purpose = tool_purpose,
        timestamp = db_model.timestamp,
        model_cost_credits = db_model.model_cost_credits,
        remote_runtime_cost_credits = db_model.remote_runtime_cost_credits,
        api_call_cost_credits = db_model.api_call_cost_credits,
        maintenance_fee_credits = db_model.maintenance_fee_credits,
        total_cost_credits = db_model.total_cost_credits,
        runtime_seconds = db_model.runtime_seconds,
        remote_runtime_seconds = db_model.remote_runtime_seconds,
        input_tokens = db_model.input_tokens,
        output_tokens = db_model.output_tokens,
        search_tokens = db_model.search_tokens,
        total_tokens = db_model.total_tokens,
        output_image_sizes = db_model.output_image_sizes,
        input_image_sizes = db_model.input_image_sizes,
    )


def db(domain_model: UsageRecord | None) -> UsageRecordDB | None:
    if domain_model is None:
        return None

    return UsageRecordDB(
        user_id = domain_model.user_id,
        payer_id = domain_model.payer_id,
        uses_credits = domain_model.uses_credits,
        is_failed = domain_model.is_failed,
        chat_id = domain_model.chat_id,
        tool_id = domain_model.tool.id,
        tool_name = domain_model.tool.name,
        provider_id = domain_model.tool.provider.id,
        provider_name = domain_model.tool.provider.name,
        purpose = domain_model.tool_purpose.value,
        timestamp = domain_model.timestamp,
        runtime_seconds = domain_model.runtime_seconds,
        remote_runtime_seconds = domain_model.remote_runtime_seconds,
        model_cost_credits = domain_model.model_cost_credits,
        remote_runtime_cost_credits = domain_model.remote_runtime_cost_credits,
        api_call_cost_credits = domain_model.api_call_cost_credits,
        maintenance_fee_credits = domain_model.maintenance_fee_credits,
        total_cost_credits = domain_model.total_cost_credits,
        input_tokens = domain_model.input_tokens,
        output_tokens = domain_model.output_tokens,
        search_tokens = domain_model.search_tokens,
        total_tokens = domain_model.total_tokens,
        output_image_sizes = domain_model.output_image_sizes,
        input_image_sizes = domain_model.input_image_sizes,
    )
