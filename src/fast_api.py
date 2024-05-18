from fastapi import Depends, FastAPI, Query
from pydantic import HttpUrl

from api.auth import verify_api_key
from features.web_fetcher import WebFetcher
from util.config import instance as config

app = FastAPI()


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
