from fastapi import Depends, FastAPI, HTTPException
from starlette.responses import RedirectResponse

from db.crud.chat_config import ChatConfigCRUD
from db.crud.chat_message import ChatMessageCRUD
from db.crud.tools_cache import ToolsCacheCRUD
from db.crud.user import UserCRUD
from db.sql import get_session
from features.auth import verify_api_key
from features.chat.telegram.domain_langchain_mapper import DomainLangchainMapper
from features.chat.telegram.model.update import Update
from features.chat.telegram.telegram_bot_api import TelegramBotAPI
from features.chat.telegram.telegram_data_resolver import TelegramDataResolver
from features.chat.telegram.telegram_domain_mapper import TelegramDomainMapper
from features.chat.telegram.telegram_summary_responder import respond_with_summary
from features.chat.telegram.telegram_update_responder import respond_to_update
from features.summarizer.raw_notes_payload import RawNotesPayload
from util.config import config
from util.safe_printer_mixin import sprint
from util.translations_cache import TranslationsCache

app = FastAPI(
    docs_url = None,
    redoc_url = None,
    title = "The Agent's API",
    description = "This is the API service for The Agent.",
    debug = config.verbose,
)


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url = config.website_url)


@app.get("/health")
def health() -> dict: return {"status": "ok"}


@app.post("/telegram/chat-update")
def telegram_chat_update(
    update: Update,
    db = Depends(get_session),
) -> bool:
    telegram_bot_api = TelegramBotAPI()
    return respond_to_update(
        user_dao = UserCRUD(db),
        chat_messages_dao = ChatMessageCRUD(db),
        telegram_domain_mapper = TelegramDomainMapper(),
        telegram_data_resolver = TelegramDataResolver(db, telegram_bot_api),
        domain_langchain_mapper = DomainLangchainMapper(),
        telegram_bot_api = telegram_bot_api,
        update = update,
    )


@app.post("/notify/release")
def notify_of_release(
    payload: RawNotesPayload,
    _ = Depends(verify_api_key),
    db = Depends(get_session),
) -> dict:
    return respond_with_summary(
        chat_config_dao = ChatConfigCRUD(db),
        chat_message_dao = ChatMessageCRUD(db),
        telegram_bot_api = TelegramBotAPI(),
        translations = TranslationsCache(),
        payload = payload,
    )


@app.post("/task/clear-expired-cache")
def clear_expired_cache(
    _ = Depends(verify_api_key),
    db = Depends(get_session),
) -> dict:
    try:
        cleared_count = ToolsCacheCRUD(db).delete_expired()
        sprint(f"Cleared expired cache entries: {cleared_count}")
        return {"cleared_entries_count": cleared_count}
    except Exception as e:
        sprint(f"Failed to clear expired cache", e)
        raise HTTPException(status_code = 500, detail = {"reason ": str(e)})
