import json
import traceback

from langchain_core.tools import tool

from db.crud.chat_config import ChatConfigCRUD
from db.crud.invite import InviteCRUD
from db.crud.tools_cache import ToolsCacheCRUD
from db.crud.user import UserCRUD
from db.schema.chat_config import ChatConfig, ChatConfigSave
from db.sql import get_detached_session
from features.chat.tools.base_tool_binder import BaseToolBinder
from features.html_content_cleaner import HTMLContentCleaner
from features.invite_manager import InviteManager
from features.web_fetcher import WebFetcher

TOOL_TRUNCATE_LENGTH = 8192  # to save some tokens


@tool
def invite_friend(user_id: str, friend_telegram_username: str) -> str:
    """
    Invites a friend to the chatbot.

    Args:
        user_id: A unique identifier of the user/author, usually found in the metadata
        friend_telegram_username: [mandatory] The Telegram username of the friend to invite, without '@'
    """
    try:
        with get_detached_session() as db:
            invite_manager = InviteManager(UserCRUD(db), InviteCRUD(db))
            result, message = invite_manager.invite_user(user_id, friend_telegram_username)
            if result == InviteManager.Result.failure:
                return json.dumps({"result": "Failure", "reason": message})
            return json.dumps({"result": "Success", "next_step": message})
    except Exception as e:
        traceback.print_exc()
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def uninvite_friend(user_id: str, friend_telegram_username: str) -> str:
    """
    Uninvites a friend from the chatbot.

    Args:
        user_id: A unique identifier of the user/author, usually found in the metadata
        friend_telegram_username: [mandatory] The Telegram username of the friend to uninvite, without '@'
    """
    try:
        with get_detached_session() as db:
            invite_manager = InviteManager(UserCRUD(db), InviteCRUD(db))
            result, message = invite_manager.uninvite_user(user_id, friend_telegram_username)
            if result == InviteManager.Result.failure:
                return json.dumps({"result": "Failure", "reason": message})
            return json.dumps({"result": "Success", "next_step": message})
    except Exception as e:
        traceback.print_exc()
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def change_chat_language(chat_id: str, langauge_name: str, language_iso_code: str | None = None) -> str:
    """
    Changes the chat's main language, whether directly or indirectly requested by a user.

    Args:
        chat_id: [mandatory] A unique identifier of the chat, usually found in the metadata
        langauge_name: [mandatory] The name of the preferred language, in English
        language_iso_code: [optional] The 2-character ISO code of the preferred language, if known
    """
    try:
        with get_detached_session() as db:
            chat_config_dao = ChatConfigCRUD(db)
            chat_config_db = chat_config_dao.get(chat_id)
            if not chat_config_db:
                return json.dumps({"result": "Failure", "reason": "Chat not found"})
            chat_config = ChatConfig.model_validate(chat_config_db)
            chat_config.language_name = langauge_name
            chat_config.language_iso_code = language_iso_code
            chat_config_db = chat_config_dao.save(ChatConfigSave(**chat_config.model_dump()))
            chat_config = ChatConfig.model_validate(chat_config_db)
            return json.dumps(
                {
                    "result": "Success",
                    "language_iso_code": chat_config.language_iso_code,
                    "language_name": chat_config.language_name,
                }
            )
    except Exception as e:
        traceback.print_exc()
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def change_chat_reply_chance(chat_id: str, reply_chance_percent: int) -> str:
    """
    Changes the bot's chance (in percent) to reply to this chat.

    Args:
        chat_id: [mandatory] A unique identifier of the chat, usually found in the metadata
        reply_chance_percent: [mandatory] The chance, in percent [0-100], for the bot to reply to this chat
    """
    try:
        if (reply_chance_percent < 0) or (reply_chance_percent > 100):
            return json.dumps({"result": "Failure", "reason": "Invalid reply chance percent, must be in [0-100]"})
        with get_detached_session() as db:
            chat_config_dao = ChatConfigCRUD(db)
            chat_config_db = chat_config_dao.get(chat_id)
            if not chat_config_db:
                return json.dumps({"result": "Failure", "reason": "Chat not found"})
            chat_config = ChatConfig.model_validate(chat_config_db)
            chat_config.reply_chance_percent = reply_chance_percent
            chat_config_db = chat_config_dao.save(ChatConfigSave(**chat_config.model_dump()))
            chat_config = ChatConfig.model_validate(chat_config_db)
            return json.dumps(
                {
                    "result": "Success",
                    "reply_chance_percent": chat_config.language_iso_code,
                }
            )
    except Exception as e:
        traceback.print_exc()
        return json.dumps({"result": "Error", "error": str(e)})


@tool
def fetch_web_content(url: str) -> str:
    """
    Fetches the text content from the given web page URL.

    Args:
        url: [mandatory] The URL of the web page
    """
    try:
        with get_detached_session() as db:
            tools_cache_dao = ToolsCacheCRUD(db)
            html = WebFetcher(url, tools_cache_dao, auto_fetch_html = True).html
            text = HTMLContentCleaner(str(html), tools_cache_dao).clean_up()
            result = text[:TOOL_TRUNCATE_LENGTH] + '...' if len(text) > TOOL_TRUNCATE_LENGTH else text
            return json.dumps({"result": "Success", "content": result})
    except Exception as e:
        traceback.print_exc()
        return json.dumps({"result": "Error", "error": str(e)})


class ToolsLibrary(BaseToolBinder):

    def __init__(self):
        super().__init__(
            {
                "invite_friend": invite_friend,
                "uninvite_friend": uninvite_friend,
                "change_chat_language": change_chat_language,
                "change_chat_reply_chance": change_chat_reply_chance,
                "fetch_web_content": fetch_web_content,
            }
        )
