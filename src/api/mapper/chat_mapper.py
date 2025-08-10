from api.model.chat_settings_response import ChatSettingsResponse
from db.schema.chat_config import ChatConfig


def domain_to_api(chat: ChatConfig, is_own: bool) -> ChatSettingsResponse:
    return ChatSettingsResponse(
        chat_id = chat.chat_id.hex,
        title = chat.title,
        language_name = chat.language_name,
        language_iso_code = chat.language_iso_code,
        reply_chance_percent = chat.reply_chance_percent,
        release_notifications = chat.release_notifications.value,
        is_private = chat.is_private,
        is_own = is_own,
    )
