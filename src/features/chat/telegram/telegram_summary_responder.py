import base64

from db.crud.chat_config import ChatConfigCRUD
from db.schema.chat_config import ChatConfig
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.release_summarizer.raw_notes_payload import RawNotesPayload
from features.release_summarizer.release_summarizer import ReleaseSummarizer
from util.safe_printer_mixin import sprint
from util.translations_cache import TranslationsCache, DEFAULT_LANGUAGE, DEFAULT_ISO_CODE


def respond_with_summary(
    chat_config_dao: ChatConfigCRUD,
    telegram_bot_sdk: TelegramBotSDK,
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
        sprint("Release summary failed for default language", e)

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
            telegram_bot_sdk.send_text_message(chat.chat_id, summary)
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
