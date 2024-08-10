import json
import traceback

from langchain_core.tools import tool

from db.crud.tools_cache import ToolsCacheCRUD
from db.sql import get_detached_session
from features.chat.tools.base_tool_binder import BaseToolBinder
from features.html_content_cleaner import HTMLContentCleaner
from features.web_fetcher import WebFetcher

TOOL_TRUNCATE_LENGTH = 8192  # to save some tokens


@tool
def fetch_web_content(url: str) -> str:
    """
    Fetches the text content from the given web page URL.

    Args:
        url: [mandatory] The URL of the web page
    """
    try:
        with get_detached_session() as db:
            tools_cache_dao = ToolsCacheCRUD(db)
            html = WebFetcher(url, tools_cache_dao, auto_fetch_html = True).html
            text = HTMLContentCleaner(str(html), tools_cache_dao).clean_up()
            result = text[:TOOL_TRUNCATE_LENGTH] + '...' if len(text) > TOOL_TRUNCATE_LENGTH else text
            return json.dumps({"result": "Success", "content": result})
    except Exception as e:
        traceback.print_exc()
        return json.dumps({"result": "Error", "error": str(e)})


class ToolsLibrary(BaseToolBinder):

    def __init__(self):
        super().__init__(
            {
                "fetch_web_content": fetch_web_content,
            }
        )
