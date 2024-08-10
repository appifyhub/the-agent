import json

from langchain_core.tools import tool

from db.crud.tools_cache import ToolsCacheCRUD
from db.sql import get_detached_session
from features.chat.tools.base_tool_binder import BaseToolBinder
from features.web_fetcher import WebFetcher


@tool
def fetch_web_page_html(url: str) -> str:
    """
    Fetches the HTML contents of the given web page URL.

    Args:
        url: [mandatory] The URL of the web page
    """
    try:
        with get_detached_session() as db:
            tools_cache_dao = ToolsCacheCRUD(db)
            fetcher = WebFetcher(url, tools_cache_dao, auto_fetch_html = True)
            return json.dumps({"result": "OK", "content": fetcher.html})
    except Exception as e:
        return json.dumps({"result": "Error", "error": str(e)})


class ToolsLibrary(BaseToolBinder):

    def __init__(self):
        super().__init__(
            {
                "fetch_web_page_html": fetch_web_page_html,
            }
        )
