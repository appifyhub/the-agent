import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from db.crud.tools_cache import ToolsCacheCRUD
from db.schema.tools_cache import ToolsCache
from di.di import DI
from features.web_browsing.html_content_cleaner import CACHE_TTL, HTMLContentCleaner


class HTMLContentCleanerTest(unittest.TestCase):
    mock_di: DI
    mock_cache_crud: ToolsCacheCRUD
    sample_html: str
    cache_entry: ToolsCache

    def setUp(self):
        self.mock_cache_crud = MagicMock()
        self.sample_html = "<html><body><h1>Title</h1><p>Some content.</p></body></html>"
        self.cache_entry = ToolsCache(
            key = "test_cache_key",
            value = "Processed Content",
            expires_at = datetime.now() + CACHE_TTL,
        )
        self.mock_cache_crud.create_key.return_value = "test_cache_key"
        self.mock_di = MagicMock(spec = DI)
        # noinspection PyPropertyAccess
        self.mock_di.tools_cache_crud = self.mock_cache_crud

    def test_clean_up_cache_miss(self):
        self.mock_cache_crud.get.return_value = None
        cleaner = HTMLContentCleaner(self.sample_html, self.mock_di)
        result = cleaner.clean_up()
        self.assertIn("# Title", result)
        self.assertIn("Some content", result)
        # noinspection PyUnresolvedReferences
        self.mock_cache_crud.save.assert_called_once()

    def test_clean_up_cache_hit(self):
        self.mock_cache_crud.get.return_value = self.cache_entry.model_dump()
        cleaner = HTMLContentCleaner(self.sample_html, self.mock_di)
        result = cleaner.clean_up()
        self.assertEqual(result, "Processed Content")
        # noinspection PyUnresolvedReferences
        self.mock_cache_crud.save.assert_not_called()

    def test_clean_up_expired_cache(self):
        expired_cache_entry = ToolsCache(
            key = "test_cache_key",
            value = "Processed Content",
            expires_at = datetime.now() - timedelta(days = 1),  # Expired cache
        )
        self.mock_cache_crud.get.return_value = expired_cache_entry.model_dump()
        cleaner = HTMLContentCleaner(self.sample_html, self.mock_di)
        result = cleaner.clean_up()
        self.assertIn("# Title", result)
        self.assertIn("Some content", result)
        # noinspection PyUnresolvedReferences
        self.mock_cache_crud.save.assert_called_once()

    def test_clean_up_markup_conversion(self):
        html = "<h1>Header1</h1><h2>Header2</h2><h3>Header3</h3><a href=\"https://example.com\">Link</a>"
        self.mock_cache_crud.get.return_value = None  # Simulate cache miss
        cleaner = HTMLContentCleaner(html, self.mock_di)
        result = cleaner.clean_up()
        self.assertIn("# Header1", result)
        self.assertIn("## Header2", result)
        self.assertIn("### Header3", result)
        self.assertIn("Link", result)  # Links get removed by the Readability lib

    def test_remove_navigational_elements(self):
        html = "<nav>Navigation</nav><header>Header</header><menu>Menu</menu><div class=\"menu\">Menu div</div>"
        content = HTMLContentCleaner._remove_menus(html)
        self.assertNotIn("Navigation", content)
        self.assertNotIn("Header", content)
        self.assertNotIn("Menu", content)
        self.assertNotIn("Menu div", content)
