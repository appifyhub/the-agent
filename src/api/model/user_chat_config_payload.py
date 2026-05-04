from pydantic import BaseModel


class UserChatConfigPayload(BaseModel):
    use_about_me: bool
    use_custom_prompt: bool
