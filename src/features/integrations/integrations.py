from db.model.chat_config import ChatConfigDB
from db.schema.user import UserSave
from features.integrations.integration_config import TELEGRAM_AGENT


def resolve_agent_user(chat_type: ChatConfigDB.ChatType) -> UserSave:
    match chat_type:
        case ChatConfigDB.ChatType.telegram:
            return TELEGRAM_AGENT
    raise ValueError(f"Unsupported chat type: {chat_type}")
