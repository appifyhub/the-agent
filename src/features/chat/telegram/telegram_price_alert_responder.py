import json

from db.crud.chat_config import ChatConfigCRUD
from db.crud.price_alert import PriceAlertCRUD
from db.crud.tools_cache import ToolsCacheCRUD
from db.crud.user import UserCRUD
from db.schema.chat_config import ChatConfig
from features.announcements.information_announcer import InformationAnnouncer
from features.chat.price_alert_manager import PriceAlertManager
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.currencies.exchange_rate_fetcher import ExchangeRateFetcher
from util.safe_printer_mixin import sprint
from util.translations_cache import DEFAULT_ISO_CODE, DEFAULT_LANGUAGE, TranslationsCache


def respond_with_announcements(
    user_dao: UserCRUD,
    chat_config_dao: ChatConfigCRUD,
    price_alert_dao: PriceAlertCRUD,
    tools_cache_dao: ToolsCacheCRUD,
    telegram_bot_sdk: TelegramBotSDK,
    translations: TranslationsCache,
) -> dict:
    rate_fetcher = ExchangeRateFetcher(None, user_dao, tools_cache_dao)
    triggered_alerts = PriceAlertManager.check_triggered_alerts(
        chat_id = None,
        fetcher = rate_fetcher,
        price_alert_dao = price_alert_dao,
    )

    announcements_created: int = 0
    chats_notified: int = 0
    for alert in triggered_alerts:
        # try to summarize the announcement first
        try:
            chat_config_db = chat_config_dao.get(alert.chat_id)
            if not chat_config_db:
                raise ValueError(f"Chat config not found for chat {alert.chat_id}")
            chat_config = ChatConfig.model_validate(chat_config_db)

            language_name = chat_config.language_name or DEFAULT_LANGUAGE
            language_iso_code = chat_config.language_iso_code or DEFAULT_ISO_CODE
            announcement_text = translations.get(language_name, language_iso_code)
            if announcement_text:
                sprint(f"Announcement already cached for chat {alert.chat_id}")
            else:
                sprint(f"No cached announcement available for chat {alert.chat_id}")
                raw_information = json.dumps(alert.model_dump())
                answer = InformationAnnouncer(raw_information, language_name, language_iso_code).execute()
                if not answer.content:
                    raise ValueError("LLM Answer not received")
                announcement_text = translations.save(answer.content, language_name, language_iso_code)
                announcements_created += 1
        except Exception as e:
            sprint("Price alert announcement failed", e)
            continue

        # now let's send the announcement to each chat
        try:
            telegram_bot_sdk.send_text_message(alert.chat_id, announcement_text)
            chats_notified += 1
        except Exception as e:
            sprint(f"Chat notification failed for chat #{alert.chat_id}", e)

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
