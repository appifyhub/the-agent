import base64
import traceback
from datetime import datetime

from fastapi import Depends, FastAPI, Query, HTTPException
from pydantic import HttpUrl
from starlette.responses import RedirectResponse

from db.crud.chat_config import ChatConfigCRUD
from db.crud.chat_message import ChatMessageCRUD
from db.crud.chat_message_attachment import ChatMessageAttachmentCRUD
from db.crud.invite import InviteCRUD
from db.crud.user import UserCRUD
from db.schema.chat_config import ChatConfig
from db.schema.chat_message import ChatMessage, ChatMessageSave
from db.schema.chat_message_attachment import ChatMessageAttachment
from db.schema.invite import Invite
from db.schema.user import User
from db.sql import get_session
from features.auth import verify_api_key
from features.chat.telegram.langchain_telegram_mapper import LangChainTelegramMapper
from features.chat.telegram.model.update import Update
from features.chat.telegram.telegram_bot_api import TelegramBotAPI
from features.chat.telegram.telegram_chat_bot import TelegramChatBot
from features.chat.telegram.telegram_data_resolver import TelegramDataResolver
from features.chat.telegram.telegram_update_mapper import TelegramUpdateMapper
from features.command_processor import CommandProcessor
from features.prompting.predefined_prompts import TELEGRAM_BOT_USER
from features.summarizer.raw_notes_payload import RawNotesPayload
from features.summarizer.release_summarizer import ReleaseSummarizer
from features.web_fetcher import WebFetcher
from util.config import config
from util.functions import construct_bot_message_id
from util.safe_printer_mixin import SafePrinterMixin
from util.translations_cache import TranslationsCache, DEFAULT_LANGUAGE, DEFAULT_ISO_CODE

telegram_bot_api = TelegramBotAPI()
app = FastAPI(
    docs_url = None,
    redoc_url = None,
    title = "The Agent's API",
    description = "This is the API service for The Agent.",
    debug = config.verbose,
)


def sprint(content: str, e: Exception | None = None):
    printer = SafePrinterMixin(config.verbose)
    printer.sprint(content)
    if e:
        printer.sprint(str(e))
        if config.verbose:
            traceback.print_exc()


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url = config.website_url)


@app.get("/health")
def health() -> dict: return {"status": "ok"}


# not accessible in production
@app.get("/debug/html-fetcher")
def html_fetcher(
    url: HttpUrl = Query(...),
    _ = Depends(verify_api_key),
) -> dict:
    fetcher = WebFetcher(url, auto_fetch_html = True)
    return {"url": url, "html": fetcher.html}


# not accessible in production
@app.get("/debug/json-fetcher")
def json_fetcher(
    url: HttpUrl = Query(...),
    _ = Depends(verify_api_key),
) -> dict:
    fetcher = WebFetcher(url, auto_fetch_json = True)
    return {"url": url, "json": fetcher.json}


# not accessible in production
@app.get("/debug/users")
def get_users(
    skip: int = Query(0),
    limit: int = Query(100),
    _ = Depends(verify_api_key),
    db = Depends(get_session),
) -> list[User]:
    users_db = UserCRUD(db).get_all(skip = skip, limit = limit)
    return [User.model_validate(user) for user in users_db]


# not accessible in production
@app.get("/debug/chat-messages")
def get_chat_messages(
    skip: int = Query(0),
    limit: int = Query(100),
    _ = Depends(verify_api_key),
    db = Depends(get_session),
) -> list[ChatMessage]:
    chat_messages_db = ChatMessageCRUD(db).get_all(skip = skip, limit = limit)
    return [ChatMessage.model_validate(chat_message) for chat_message in chat_messages_db]


# not accessible in production
@app.get("/debug/chat-message-attachments")
def get_chat_messages(
    _ = Depends(verify_api_key),
    db = Depends(get_session),
    skip: int = Query(0),
    limit: int = Query(100),
) -> list[ChatMessageAttachment]:
    chat_message_attachments_db = ChatMessageAttachmentCRUD(db).get_all(skip = skip, limit = limit)
    return [
        ChatMessageAttachment.model_validate(chat_message_attachment)
        for chat_message_attachment in chat_message_attachments_db
    ]


# not accessible in production
@app.get("/debug/chats")
def get_chat_messages(
    _ = Depends(verify_api_key),
    db = Depends(get_session),
    skip: int = Query(0),
    limit: int = Query(100),
) -> list[ChatConfig]:
    chat_config_db = ChatConfigCRUD(db).get_all(skip = skip, limit = limit)
    return [ChatConfig.model_validate(chat_config) for chat_config in chat_config_db]


# not accessible in production
@app.get("/debug/invites")
def get_chat_messages(
    _ = Depends(verify_api_key),
    db = Depends(get_session),
    skip: int = Query(0),
    limit: int = Query(100),
) -> list[Invite]:
    invite_db = InviteCRUD(db).get_all(skip = skip, limit = limit)
    return [Invite.model_validate(invite) for invite in invite_db]


@app.post("/telegram/chat-update")
def telegram_chat_update(
    update: Update,
    db = Depends(get_session),
) -> bool:
    try:
        # map to storage models for persistence
        mapped_update = TelegramUpdateMapper().convert_update(update)
        if not mapped_update: raise HTTPException(status_code = 422, detail = "Update not convertible")

        # store and map to domain models (throws in case of error)
        telegram_data_resolver = TelegramDataResolver(db, telegram_bot_api)
        resolved_update = telegram_data_resolver.resolve(mapped_update)
        sprint(f"Imported updates from Telegram: {resolved_update}")

        # fetch latest messages to prepare a response
        chat_messages_dao = ChatMessageCRUD(db)
        user_dao = UserCRUD(db)
        past_messages_db = chat_messages_dao.get_latest_chat_messages(
            chat_id = resolved_update.chat.chat_id,
            limit = config.chat_history_depth,
        )
        past_messages = [ChatMessage.model_validate(chat_message) for chat_message in past_messages_db]
        langchain_telegram_mapper = LangChainTelegramMapper()
        author_of = lambda message: UserCRUD(db).get(message.author_id)
        convert = lambda message: langchain_telegram_mapper.map_to_langchain(author_of(message), message)
        langchain_messages = [convert(message) for message in past_messages][::-1]  # DB sorting is date descending

        # process the update and respond
        if not resolved_update.author:
            sprint("Not responding to messages without author")
            return False
        UserCRUD(db).save(TELEGRAM_BOT_USER)  # save is ignored if it already exists
        command_processor = CommandProcessor(resolved_update.author, user_dao)
        telegram_chat_bot = TelegramChatBot(resolved_update.author, langchain_messages, command_processor)
        raw_message_response = telegram_chat_bot.execute()
        messages_to_send = langchain_telegram_mapper.map_bot_message_to_storage(
            resolved_update.chat.chat_id,
            raw_message_response,
        )
        sent_messages: int = 0
        saved_messages: int = 0
        for message in messages_to_send:
            telegram_bot_api.send_text_message(message.chat_id, message.text)
            sent_messages += 1
            chat_messages_dao.save(message)
            saved_messages += 1
        sprint(f"Used {len(past_messages_db)}, saved {saved_messages}, sent {sent_messages} messages")
        sprint(f"Finished responding to event: \n[{config.telegram_bot_name}]: {raw_message_response.content}")
        return True
    except Exception as e:
        sprint(f"Failed to ingest: {update}", e)
        return False


@app.post("/notify/release")
def notify_of_release(
    payload: RawNotesPayload,
    _ = Depends(verify_api_key),
    db = Depends(get_session),
) -> dict:
    latest_chats_db = ChatConfigCRUD(db).get_all(limit = 1024)
    latest_chats = [ChatConfig.model_validate(chat) for chat in latest_chats_db]
    translations = TranslationsCache()
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
            ChatMessageCRUD(db).save(message_to_store)
            chats_notified += 1
        except Exception as e:
            sprint(f"Chat notification failed for chat #{chat.chat_id}", e)
    # we're done, report back
    sprint(f"Chats: {len(latest_chats)}, summaries created: {summaries_created}, notified: {chats_notified}")
    return {
        "summary": translations.get(),  # fetches default language
        "chats_selected": len(latest_chats),
        "chats_notified": chats_notified,
        "summaries_created": summaries_created,
    }
