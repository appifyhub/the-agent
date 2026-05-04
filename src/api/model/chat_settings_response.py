from pydantic import BaseModel

from api.model.chat_config_response import ChatConfigResponse
from api.model.user_chat_config_response import UserChatConfigResponse


class ChatSettingsResponse(BaseModel):
    chat_config: ChatConfigResponse
    user_chat_config: UserChatConfigResponse
