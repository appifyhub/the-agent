from fastapi import Depends, FastAPI, Query
from pydantic import HttpUrl
from starlette.responses import RedirectResponse

from api.auth import verify_api_key
from chat.telegram.model.update import Update
from db.crud.user import UserCRUD
from db.schema.user import User
from db.sql import get_session
from features.web_fetcher import WebFetcher
from util.config import config

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


@app.get("/html-fetcher")
def html_fetcher(
    url: HttpUrl = Query(...),
    _ = Depends(verify_api_key),
) -> dict:
    fetcher = WebFetcher(url, config, auto_fetch_html = True)
    return {"url": url, "html": fetcher.html}


@app.get("/json-fetcher")
def json_fetcher(
    url: HttpUrl = Query(...),
    _ = Depends(verify_api_key),
) -> dict:
    fetcher = WebFetcher(url, config, auto_fetch_json = True)
    return {"url": url, "json": fetcher.json}


@app.get("/users")
def get_users(
    _ = Depends(verify_api_key),
    db = Depends(get_session),
    skip: int = Query(0),
    limit: int = Query(100),
) -> list[str]:
    users_db = UserCRUD(db).get_all(skip = skip, limit = limit)
    users = [User.model_validate(user) for user in users_db]
    return [f"@{user.telegram_username}" for user in users]


@app.post("/telegram/chat-update")
def telegram_chat_update(update: Update) -> Update:
    return update
