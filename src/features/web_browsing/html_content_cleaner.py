import re
from datetime import timedelta, datetime

from readabilipy import simple_json_from_html_string

from db.crud.tools_cache import ToolsCacheCRUD
from db.schema.tools_cache import ToolsCache, ToolsCacheSave
from util.config import config
from util.functions import digest_md5
from util.safe_printer_mixin import SafePrinterMixin

CACHE_PREFIX = "html-content-cleaner"
CACHE_TTL = timedelta(weeks = 52)


class HTMLContentCleaner(SafePrinterMixin):
    raw_html: str
    plain_text: str
    __cache_dao: ToolsCacheCRUD

    def __init__(
        self,
        raw_html: str,
        cache_dao: ToolsCacheCRUD,
    ):
        super().__init__(config.verbose)
        self.raw_html = raw_html
        self.plain_text = ""
        self.__cache_dao = cache_dao

    def clean_up(self) -> str:
        self.plain_text = ""  # reset value

        cache_key = self.__cache_dao.create_key(CACHE_PREFIX, digest_md5(self.raw_html))
        cache_entry_db = self.__cache_dao.get(cache_key)
        if cache_entry_db:
            cache_entry = ToolsCache.model_validate(cache_entry_db)
            if not cache_entry.is_expired():
                self.sprint(f"Cache hit for '{cache_key}'")
                self.plain_text = cache_entry.value
                return self.plain_text
            self.sprint(f"Cache expired for '{cache_key}'")
        self.sprint(f"Cache miss for '{cache_key}'")

        content_json = simple_json_from_html_string(self.raw_html)
        self.sprint(f"Processed HTML, received {len(content_json)} content items")
        # replace HTML markers with Markdown markers
        self.plain_text = re.sub(r"<h1>(.*?)</h1>", r"\n# \1\n", content_json["plain_content"])
        self.plain_text = re.sub(r"<h2>(.*?)</h2>", r"\n## \1\n", self.plain_text)
        self.plain_text = re.sub(r"<h3>(.*?)</h3>", r"\n### \1\n", self.plain_text)
        self.plain_text = re.sub(r"<h4>(.*?)</h4>", r"\n#### \1\n", self.plain_text)
        self.plain_text = re.sub(r"<h5>(.*?)</h5>", r"\n##### \1\n", self.plain_text)
        self.plain_text = re.sub(r"<h6>(.*?)</h6>", r"\n###### \1\n", self.plain_text)
        self.plain_text = re.sub(r"<a\s+(?:[^>]*?\s+)?href=\"([^\"]*)\"[^>]*>(.*?)</a>", r"[\2](\1)", self.plain_text)
        # clean other tags
        self.plain_text = self._remove_menus(self.plain_text)  # navigation components
        self.plain_text = re.sub(r"<li>(.*?)</li>", r"\n- \1\n", self.plain_text)  # list items
        self.plain_text = re.sub(r"<[ou]l>\s*</[ou]l>", '', self.plain_text)  # empty lists
        self.plain_text = re.sub(r"<[^>]+>", " ", self.plain_text)  # remove remaining tags
        # remove extra whitespace
        self.plain_text = re.sub(r"\n\s*\n+", "\n", self.plain_text)  # empty newlines
        self.plain_text = re.sub(r"[ \t]+", " ", self.plain_text).strip()  # horizontal spaces
        self.__cache_dao.save(
            ToolsCacheSave(
                key = cache_key,
                value = self.plain_text,
                expires_at = datetime.now() + CACHE_TTL,
            )
        )
        self.sprint(f"Cleaned up HTML contents, received {len(self.plain_text)} content items")
        return self.plain_text

    @staticmethod
    def _remove_menus(html):
        patterns = [
            r'<nav\b[^>]*>.*?</nav>',
            r'<header\b[^>]*>.*?</header>',
            r'<menu\b[^>]*>.*?</menu>',
            r'<div\b[^>]*class=["\'](?:[^"\']*)(?:menu|navigation|navbar|nav-bar|nav)(?:[^"\']*)["\'][^>]*>.*?</div>',
            r'<ul\b[^>]*class=["\'](?:[^"\']*)(?:menu|navigation|navbar|nav-bar|nav)(?:[^"\']*)["\'][^>]*>.*?</ul>',
            r'<div\b[^>]*id=["\'](?:menu|nav)(?:[^"\']*)["\'][^>]*>.*?</div>',
        ]
        result = html
        for pattern in patterns:
            result = re.sub(pattern, '', result, flags = re.DOTALL | re.IGNORECASE)
        return result
