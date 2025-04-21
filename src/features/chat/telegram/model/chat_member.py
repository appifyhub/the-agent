from typing import Union, Literal

from pydantic import BaseModel

from features.chat.telegram.model.user import User


class ChatMemberBase(BaseModel):
    """https://core.telegram.org/bots/api#chatmember"""
    status: str
    user: User


class ChatMemberOwner(ChatMemberBase):
    """https://core.telegram.org/bots/api#chatmemberowner"""
    status: Literal["creator"]
    is_anonymous: bool
    custom_title: str | None = None


class ChatMemberAdministrator(ChatMemberBase):
    """https://core.telegram.org/bots/api#chatmemberadministrator"""
    status: Literal["administrator"]
    can_be_edited: bool
    is_anonymous: bool
    can_manage_chat: bool
    can_delete_messages: bool
    can_manage_video_chats: bool
    can_restrict_members: bool
    can_promote_members: bool
    can_change_info: bool
    can_invite_users: bool
    can_post_stories: bool
    can_edit_stories: bool
    can_delete_stories: bool
    can_post_messages: bool | None = None
    can_edit_messages: bool | None = None
    can_pin_messages: bool | None = None
    can_manage_topics: bool | None = None
    custom_title: str | None = None


class ChatMemberMember(ChatMemberBase):
    """https://core.telegram.org/bots/api#chatmembermember"""
    status: Literal["member"]
    until_date: int | None = None


class ChatMemberRestricted(ChatMemberBase):
    """https://core.telegram.org/bots/api#chatmemberrestricted"""
    status: Literal["restricted"]
    is_member: bool
    can_send_messages: bool
    can_send_audios: bool
    can_send_documents: bool
    can_send_photos: bool
    can_send_videos: bool
    can_send_video_notes: bool
    can_send_voice_notes: bool
    can_send_polls: bool
    can_send_other_messages: bool
    can_add_web_page_previews: bool
    can_change_info: bool
    can_invite_users: bool
    can_pin_messages: bool
    can_manage_topics: bool
    until_date: int


class ChatMemberLeft(ChatMemberBase):
    """https://core.telegram.org/bots/api#chatmemberleft"""
    status: Literal["left"]


class ChatMemberBanned(ChatMemberBase):
    """https://core.telegram.org/bots/api#chatmemberbanned"""
    status: Literal["kicked"]
    until_date: int


ChatMember = Union[
    ChatMemberOwner,
    ChatMemberAdministrator,
    ChatMemberMember,
    ChatMemberRestricted,
    ChatMemberLeft,
    ChatMemberBanned,
]
