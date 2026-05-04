from pydantic import BaseModel

from api.model.chat_config_payload import ChatConfigPayload
from api.model.user_chat_config_payload import UserChatConfigPayload


class ChatSettingsPayload(BaseModel):
    chat_config: ChatConfigPayload | None = None
    user_chat_config: UserChatConfigPayload | None = None
