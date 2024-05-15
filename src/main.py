from fastapi import Depends, FastAPI, Query
from pydantic import HttpUrl

from auth import Auth
from config import Config
from web_fetcher import WebFetcher


config = Config()
Auth.config = config
app = FastAPI()

@app.get("/health")
def health() -> dict: return { "status": "ok" }

@app.get("/html-fetcher")
def html_fetcher(
    url: HttpUrl = Query(...),
    _ = Depends(Auth.get_api_key),
) -> dict:
    fetcher = WebFetcher(url, config, auto_fetch_html = True)
    return { "url": url, "html": fetcher.html }

@app.get("/json-fetcher")
def json_fetcher(
    url: HttpUrl = Query(...),
    _ = Depends(Auth.get_api_key),
) -> dict:
    fetcher = WebFetcher(url, config, auto_fetch_json = True)
    return { "url": url, "json": fetcher.json }
