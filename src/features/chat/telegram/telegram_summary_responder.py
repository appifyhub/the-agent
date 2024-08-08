import base64
from datetime import datetime

from db.crud.chat_config import ChatConfigCRUD
from db.crud.chat_message import ChatMessageCRUD
from db.schema.chat_config import ChatConfig
from db.schema.chat_message import ChatMessageSave
from features.chat.telegram.telegram_bot_api import TelegramBotAPI
from features.prompting.predefined_prompts import TELEGRAM_BOT_USER
from features.summarizer.raw_notes_payload import RawNotesPayload
from features.summarizer.release_summarizer import ReleaseSummarizer
from util.functions import construct_bot_message_id
from util.safe_printer_mixin import sprint
from util.translations_cache import TranslationsCache, DEFAULT_LANGUAGE, DEFAULT_ISO_CODE


def respond_with_summary(
    chat_config_dao: ChatConfigCRUD,
    chat_message_dao: ChatMessageCRUD,
    telegram_bot_api: TelegramBotAPI,
    translations: TranslationsCache,
    payload: RawNotesPayload,
) -> dict:
    latest_chats_db = chat_config_dao.get_all(limit = 1024)
    latest_chats = [ChatConfig.model_validate(chat) for chat in latest_chats_db]
    summaries_created: int = 0
    chats_notified: int = 0

    # translate once for the default language
    try:
        raw_notes = base64.b64decode(payload.raw_notes_b64).decode("utf-8")
        answer = ReleaseSummarizer(raw_notes, DEFAULT_LANGUAGE, DEFAULT_ISO_CODE).execute()
        if not answer.content:
            raise ValueError("LLM Answer not received")
        translations.save(answer.content)
        summaries_created += 1
    except Exception as e:
        sprint(f"Release summary failed for default language", e)

    # we also need to summarize for each language
    for chat in latest_chats:
        try:
            summary = translations.get(chat.language_name, chat.language_iso_code)
            if not summary:
                raw_notes = base64.b64decode(payload.raw_notes_b64).decode("utf-8")
                answer = ReleaseSummarizer(raw_notes, chat.language_name, chat.language_iso_code).execute()
                if not answer.content:
                    raise ValueError("LLM Answer not received")
                summary = translations.save(answer.content, chat.language_name, chat.language_iso_code)
                summaries_created += 1
        except Exception as e:
            sprint(f"Release summary failed for chat #{chat.chat_id}", e)
            continue

        # let's send a notification to each chat
        try:
            telegram_bot_api.send_text_message(chat.chat_id, summary)
            sent_at = datetime.now()
            message_to_store = ChatMessageSave(
                chat_id = chat.chat_id,
                message_id = construct_bot_message_id(chat.chat_id, sent_at),
                author_id = TELEGRAM_BOT_USER.id,
                sent_at = sent_at,
                text = summary,
            )
            chat_message_dao.save(message_to_store)
            chats_notified += 1
        except Exception as e:
            sprint(f"Chat notification failed for chat #{chat.chat_id}", e)

    # we're done, report back
    sprint(f"Chats: {len(latest_chats)}, summaries created: {summaries_created}, notified: {chats_notified}")
    return {
        "summary": translations.get(),
        "chats_selected": len(latest_chats),
        "chats_notified": chats_notified,
        "summaries_created": summaries_created,
    }
