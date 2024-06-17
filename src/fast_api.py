from fastapi import Depends, FastAPI, Query, HTTPException
from pydantic import HttpUrl
from starlette.responses import RedirectResponse

from chat.telegram.bot_api import BotAPI
from chat.telegram.converter import Converter
from chat.telegram.model.update import Update
from db.crud.chat_config import ChatConfigCRUD
from db.crud.chat_message import ChatMessageCRUD
from db.crud.chat_message_attachment import ChatMessageAttachmentCRUD
from db.crud.invite import InviteCRUD
from db.crud.user import UserCRUD
from db.schema.chat_config import ChatConfig
from db.schema.chat_message import ChatMessage
from db.schema.chat_message_attachment import ChatMessageAttachment
from db.schema.invite import Invite
from db.schema.user import User
from db.sql import get_session
from features.auth import verify_api_key
from features.chat.telegram.resolver import Resolver
from features.web_fetcher import WebFetcher
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

app = FastAPI(
    docs_url = None,
    redoc_url = None,
    title = "The Agent's API",
    description = "This is the API service for The Agent.",
    debug = config.verbose,
)

bot_api = BotAPI()


def sprint(content: str):
    printer = SafePrinterMixin(config.verbose)
    printer.sprint(content)


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
    conversion_result = Converter().convert_update(update)
    if not conversion_result: raise HTTPException(status_code = 404, detail = "Update not convertible")
    resolver = Resolver(db, bot_api)
    try:
        resolution_result = resolver.resolve(conversion_result)
        sprint(f"Imported from Telegram: {resolution_result}")
        return True
    except Exception as e:
        print(f"Failed to ingest: {update}")
        print(e)
        return False
