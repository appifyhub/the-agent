from dataclasses import dataclass
from uuid import UUID


@dataclass(kw_only = True)
class ChatMembership:
    user_id: UUID
    chat_id: UUID
    is_admin: bool = False
    use_about_me: bool = True
    use_custom_prompt: bool = True
