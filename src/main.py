from fastapi import Depends, FastAPI, Query
from pydantic import HttpUrl

from auth import Auth
from config import Config
from web_fetcher import WebFetcher


config = Config()
Auth.config = config
app = FastAPI()

@app.get("/health")
def health(): return { "status": "ok" }

@app.get("/web-fetcher")
def web_fetcher(
    url: HttpUrl = Query(...),
    _ = Depends(Auth.get_api_key),
):
    fetcher = WebFetcher(url, config, auto_fetch = True)
    return { "url": url, "html": fetcher.html }
