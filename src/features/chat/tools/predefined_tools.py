import json

from langchain_core.tools import tool

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
        fetcher = WebFetcher(url, auto_fetch_html = True)
        return json.dumps({"result": "OK", "content": fetcher.html})
    except Exception as e:
        return json.dumps({"result": "Error", "error": str(e)})


class PredefinedTools(BaseToolBinder):

    def __init__(self):
        super().__init__(
            {
                "fetch_web_page_html": fetch_web_page_html,
            }
        )
