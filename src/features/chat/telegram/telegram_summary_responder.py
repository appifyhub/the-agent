import base64
import json
import re
from enum import Enum
from typing import Any

from api.model.release_output_payload import ReleaseOutputPayload
from db.crud.chat_config import ChatConfigCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.model.chat_config import ChatConfigDB
from db.schema.chat_config import ChatConfig
from features.announcements.release_summarizer import ReleaseSummarizer
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.prompting.prompt_library import TELEGRAM_BOT_USER
from util.safe_printer_mixin import sprint
from util.translations_cache import TranslationsCache


class SummaryResult:
    summary: str
    chats_eligible: int
    chats_subscribed: int
    chats_unsubscribed: int
    chats_notified: int
    summaries_created: int

    def __init__(
        self,
        summary: str = "",
        chats_eligible: int = 0,
        chats_subscribed: int = 0,
        chats_unsubscribed: int = 0,
        chats_notified: int = 0,
        summaries_created: int = 0,
    ):
        self.summary = summary
        self.chats_eligible = chats_eligible
        self.chats_subscribed = chats_subscribed
        self.chats_unsubscribed = chats_unsubscribed
        self.chats_notified = chats_notified
        self.summaries_created = summaries_created

    def to_dict(self):
        return {
            "summary": self.summary,
            "chats_eligible": self.chats_eligible,
            "chats_subscribed": self.chats_subscribed,
            "chats_unsubscribed": self.chats_unsubscribed,
            "chats_notified": self.chats_notified,
            "summaries_created": self.summaries_created,
        }


def respond_with_summary(
    payload: ReleaseOutputPayload,
    user_dao: UserCRUD,
    chat_config_dao: ChatConfigCRUD,
    sponsorship_dao: SponsorshipCRUD,
    telegram_bot_sdk: TelegramBotSDK,
    translations: TranslationsCache,
) -> dict:
    result = SummaryResult()
    # decode the release output
    try:
        release_output_text: str = base64.b64decode(payload.release_output_b64).decode("utf-8")
        release_output_json: dict[str, Any] = json.loads(release_output_text)
        latest_version: str = release_output_json["latest_version"]
        new_target_version: str = release_output_json["new_target_version"]
        release_quality: str = release_output_json["release_quality"]
        release_notes_b64: str = release_output_json["release_notes_b64"]
        release_notes: str = base64.b64decode(release_notes_b64).decode("utf-8")
        print("Summarizing release notes:")
        print(f"    - Latest version: {latest_version}")
        print(f"    - New target version: {new_target_version}")
        print(f"    - Release quality: {release_quality}")
        print(f"    - Change log: {json.dumps(release_notes[:15])}...")
    except Exception as e:
        message = "Failed to decode release notes"
        sprint(message, e)
        result.summary = message
        return result.to_dict()

    # summarize for the default language first
    try:
        answer = ReleaseSummarizer(
            raw_notes = release_notes,
            invoker = TELEGRAM_BOT_USER.id,  # type: ignore
            target_chat = None,
            user_dao = user_dao,
            chat_config_dao = chat_config_dao,
            sponsorship_dao = sponsorship_dao,
            telegram_bot_sdk = telegram_bot_sdk,
        ).execute()
        if not answer.content:
            raise ValueError("LLM Answer not received")
        stripped_content = _strip_title_formatting(str(answer.content))
        translations.save(stripped_content)
        result.summary = stripped_content
        result.summaries_created += 1
    except Exception as e:
        message = "Release summary failed for default language"
        sprint(message, e)
        result.summary = message
        return result.to_dict()

    # prepare and filter the eligible chats
    change_type = get_version_change_type(latest_version, new_target_version)
    latest_chats_db = chat_config_dao.get_all(limit = 2048)
    latest_chats = [ChatConfig.model_validate(chat_db) for chat_db in latest_chats_db]
    subscribed_chats = [chat for chat in latest_chats if is_chat_subscribed(chat, change_type)]
    result.chats_eligible = len(latest_chats)
    result.chats_subscribed = len(subscribed_chats)
    result.chats_unsubscribed = result.chats_eligible - result.chats_subscribed

    # then summarize for each of the languages (with a translations cache)
    for chat in subscribed_chats:
        try:
            summary = translations.get(chat.language_name, chat.language_iso_code)
            if not summary:
                answer = ReleaseSummarizer(
                    raw_notes = release_notes,
                    invoker = TELEGRAM_BOT_USER.id,  # type: ignore
                    target_chat = chat,
                    user_dao = user_dao,
                    chat_config_dao = chat_config_dao,
                    sponsorship_dao = sponsorship_dao,
                    telegram_bot_sdk = telegram_bot_sdk,
                ).execute()
                if not answer.content:
                    raise ValueError("LLM Answer not received")
                stripped_content = _strip_title_formatting(str(answer.content))
                summary = translations.save(stripped_content, chat.language_name, chat.language_iso_code)
                result.summaries_created += 1
        except Exception as e:
            sprint(f"Release summary failed for chat #{chat.chat_id} in {chat.language_name}", e)
            continue

        # we need to notify each chat of the summary
        try:
            telegram_bot_sdk.send_text_message(chat.chat_id, summary)
            result.chats_notified += 1
        except Exception as e:
            sprint(f"Chat notification failed for chat #{chat.chat_id}", e)
            continue

    # and we're done, let's report back
    sprint("Summary execution completed:")
    sprint(json.dumps(result.to_dict(), indent = 2))
    return result.to_dict()


class VersionChangeType(Enum):
    major = 1
    minor = 2
    patch = 3


def get_version_change_type(old_version: str, new_version: str) -> VersionChangeType:
    """
    Returns the version difference type between two versions (major, minor, patch).
    If versions are equal, returns patch.
    """

    def parse_version(v: str):
        try:
            parts = v.strip().split(".")
            nums = [int(part) for part in parts if part.isdigit()]
            while len(nums) < 3:
                nums.append(0)
            return tuple(nums[:3])
        except Exception:
            return 0, 0, 0

    v_old = parse_version(old_version)
    v_new = parse_version(new_version)
    if v_new[0] != v_old[0]:
        return VersionChangeType.major
    if v_new[1] != v_old[1]:
        return VersionChangeType.minor
    if v_new[2] != v_old[2]:
        return VersionChangeType.patch
    return VersionChangeType.patch


def is_chat_subscribed(chat: ChatConfig, change_type: VersionChangeType) -> bool:
    """
    Returns True if the chat should be notified for this change_type.
    """
    subscription = chat.release_notifications
    if subscription == ChatConfigDB.ReleaseNotifications.all:
        return True
    if subscription == ChatConfigDB.ReleaseNotifications.none:
        return False
    if subscription == ChatConfigDB.ReleaseNotifications.major and change_type == VersionChangeType.major:
        return True
    if (subscription == ChatConfigDB.ReleaseNotifications.minor
        and change_type in (VersionChangeType.major, VersionChangeType.minor)):
        return True
    return False


def _strip_title_formatting(text: str) -> str:
    return re.sub(r"^(#\s*)+", "", text)
