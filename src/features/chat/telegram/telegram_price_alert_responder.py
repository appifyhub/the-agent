import json

from db.schema.chat_config import ChatConfig
from di.di import DI
from features.announcements.information_announcer import InformationAnnouncer
from util.safe_printer_mixin import sprint
from util.translations_cache import DEFAULT_ISO_CODE, DEFAULT_LANGUAGE, TranslationsCache


def respond_with_price_alerts(di: DI) -> dict:
    chats_notified: int = 0
    announcements_created: int = 0
    alert_manager = di.price_alert_manager(target_chat_id = None)
    triggered_alerts = alert_manager.get_triggered_alerts()
    translation_caches_all: dict[str, TranslationsCache] = {}
    for triggered_alert in triggered_alerts:
        # try to summarize the announcement first
        try:
            chat_config_db = di.chat_config_crud.get(triggered_alert.chat_id)
            if not chat_config_db:
                raise ValueError(f"Chat config not found for chat {triggered_alert.chat_id}")
            chat_config = ChatConfig.model_validate(chat_config_db)

            # find the correct translations cache for this alert
            base_currency = triggered_alert.base_currency
            desired_currency = triggered_alert.desired_currency
            alert_threshold = triggered_alert.threshold_percent
            translations_cache_key = f"{base_currency}-{desired_currency}-{alert_threshold}"

            # Get or create cache instance for this alert type
            if translations_cache_key not in translation_caches_all:
                translation_caches_all[translations_cache_key] = TranslationsCache()
            translations = translation_caches_all[translations_cache_key]

            language_name = chat_config.language_name or DEFAULT_LANGUAGE
            language_iso_code = chat_config.language_iso_code or DEFAULT_ISO_CODE
            announcement_text = translations.get(language_name, language_iso_code)
            if announcement_text:
                sprint(
                    f"Announcement already cached for alert type {translations_cache_key} "
                    f"in chat {triggered_alert.chat_id}",
                )
            else:
                sprint(
                    f"No cached announcement available for alert type {translations_cache_key} "
                    f"in chat {triggered_alert.chat_id}",
                )
                raw_information = json.dumps(triggered_alert.model_dump(mode = "json"))
                answer = InformationAnnouncer(
                    raw_information = raw_information,
                    invoker = triggered_alert.owner_id,
                    target_chat = chat_config,
                    user_dao = di.user_crud,
                    chat_config_dao = di.chat_config_crud,
                    sponsorship_dao = di.sponsorship_crud,
                    telegram_bot_sdk = di.telegram_bot_sdk,
                ).execute()
                if not answer.content:
                    raise ValueError("LLM Answer not received")
                announcement_text = translations.save(str(answer.content), language_name, language_iso_code)
                announcements_created += 1
        except Exception as e:
            sprint("Price alert announcement failed", e)
            continue

        # now let's send the announcement to each chat
        try:
            di.telegram_bot_sdk.send_text_message(triggered_alert.chat_id, announcement_text)
            chats_notified += 1
        except Exception as e:
            sprint(f"Chat notification failed for chat #{triggered_alert.chat_id}", e)

    # we're done, report back
    all_chat_ids = set([alert.chat_id for alert in triggered_alerts])
    sprint(
        f"Alerts: {len(triggered_alerts)}, "
        f"chats: {len(all_chat_ids)}, "
        f"announcements created: {announcements_created}, "
        f"notified: {chats_notified}",
    )
    return {
        "alerts_triggered": len(triggered_alerts),
        "announcements_created": announcements_created,
        "chats_affected": len(all_chat_ids),
        "chats_notified": chats_notified,
    }
