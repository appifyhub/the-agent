from pydantic import BaseModel


class UserChatConfigResponse(BaseModel):
    use_about_me: bool
    use_custom_prompt: bool
