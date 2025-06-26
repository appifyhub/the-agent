import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import requests
import requests_mock
from requests_mock.mocker import Mocker

from db.crud.tools_cache import ToolsCacheCRUD
from db.schema.tools_cache import ToolsCache
from features.external_tools.external_tool_library import TWITTER_API
from features.web_browsing.twitter_status_fetcher import CACHE_TTL, TwitterStatusFetcher
from util.config import config


class TwitterStatusFetcherTest(unittest.TestCase):
    cached_content: str
    cache_entry: ToolsCache
    mock_cache_crud: ToolsCacheCRUD
    api_url: str

    def setUp(self):
        config.web_timeout_s = 0
        config.rapid_api_token = "test_rapid_api_token"
        config.rapid_api_twitter_token = "test_twitter_api_token"
        self.cached_content = "@username · Name\n[Locale:en] \"Bio\"\n\n`\nTweet content\n`"
        self.cache_entry = ToolsCache(
            key = "test_cache_key",
            value = self.cached_content,
            expires_at = datetime.now() + CACHE_TTL,
        )
        self.mock_cache_crud = MagicMock()
        self.mock_cache_crud.create_key.return_value = "test_cache_key"
        self.api_url = f"https://{TWITTER_API.id}/base/apitools/tweetSimple"

    # noinspection PyUnusedLocal
    @patch("features.web_browsing.twitter_status_fetcher.sleep", return_value = None)
    @requests_mock.Mocker()
    def test_execute_cache_hit(self, m: Mocker, mock_sleep):
        self.mock_cache_crud.get.return_value = self.cache_entry.model_dump()
        fetcher = TwitterStatusFetcher("123456789", self.mock_cache_crud)
        result = fetcher.execute()
        self.assertEqual(result, self.cached_content)
        # noinspection PyUnresolvedReferences
        m.assert_not_called()

    # noinspection PyUnusedLocal
    @patch("features.web_browsing.twitter_status_fetcher.sleep", return_value = None)
    @requests_mock.Mocker()
    def test_execute_cache_miss(self, mock_sleep, m):
        self.mock_cache_crud.get.return_value = None
        # Mock the API response
        m.get(
            self.api_url,
            json = {
                "data": {
                    "data": {
                        "tweetResult": {
                            "result": {
                                "core": {
                                    "user_results": {
                                        "result": {
                                            "legacy": {
                                                "name": "Test User",
                                                "screen_name": "testuser",
                                                "description": "Test bio",
                                            },
                                        },
                                    },
                                },
                                "legacy": {"full_text": "Test tweet content", "lang": "en"},
                            },
                        },
                    },
                },
            },
        )
        fetcher = TwitterStatusFetcher("123456789", self.mock_cache_crud)
        result = fetcher.execute()
        expected_result = "@testuser · Test User\n[Locale:en] Bio: \"Test bio\"\n```\nTest tweet content\n```"
        self.assertEqual(result, expected_result)
        # noinspection PyUnresolvedReferences
        self.mock_cache_crud.save.assert_called_once()

    # noinspection PyUnusedLocal
    @patch("features.web_browsing.twitter_status_fetcher.sleep", return_value = None)
    @requests_mock.Mocker()
    def test_execute_api_error(self, mock_sleep, m):
        self.mock_cache_crud.get.return_value = None
        params = {
            "resFormat": "json",
            "id": "123456789",
            "apiKey": config.rapid_api_twitter_token,
            "cursor": "-1",
        }
        full_url = requests.Request("GET", self.api_url, params = params).prepare().url
        m.get(full_url, status_code = 500)
        fetcher = TwitterStatusFetcher("123456789", self.mock_cache_crud)
        with self.assertRaises(requests.exceptions.HTTPError):
            fetcher.execute()

    # noinspection PyUnusedLocal
    @patch("features.web_browsing.twitter_status_fetcher.sleep", return_value = None)
    @requests_mock.Mocker()
    def test_api_call_parameters(self, mock_sleep, m):
        self.mock_cache_crud.get.return_value = None

        m.get(
            self.api_url,
            json = {
                "data": {
                    "data": {
                        "tweetResult": {
                            "result": {"core": {"user_results": {"result": {"legacy": {}}}}, "legacy": {}},
                        },
                    },
                },
            },
        )
        fetcher = TwitterStatusFetcher("123456789", self.mock_cache_crud)
        fetcher.execute()
        if not m.request_history:
            self.fail("No requests were made")
        last_request = m.last_request

        # Check URL
        self.assertTrue(last_request.url.startswith(self.api_url))
        self.assertIn("resFormat=json", last_request.url)
        self.assertIn("id=123456789", last_request.url)
        self.assertIn(f"apiKey={config.rapid_api_twitter_token}", last_request.url)
        self.assertIn("cursor=-1", last_request.url)

        # Check headers
        self.assertEqual(last_request.headers["X-RapidAPI-Host"], TWITTER_API.id)
        self.assertEqual(last_request.headers["X-RapidAPI-Key"], config.rapid_api_token)

    # noinspection PyUnusedLocal
    @patch("features.web_browsing.twitter_status_fetcher.ComputerVisionAnalyzer")
    @requests_mock.Mocker()
    def test_resolve_photo_contents(self, mock_analyzer, m):
        # Mock the analyzer's execute method to return a fixed description
        mock_analyzer.return_value.execute.return_value = "A beautiful landscape."

        fetcher = TwitterStatusFetcher("123456789", self.mock_cache_crud)

        # Sample tweet data with photo attachments
        tweet_with_photos = {
            "extended_entities": {
                "media": [
                    {
                        "media_url_https": "https://example.com/photo1.jpg",
                        "type": "photo",
                    },
                    {
                        "media_url_https": "https://example.com/photo2.png",
                        "type": "photo",
                    },
                    {  # Non-photo attachment, should be ignored
                        "media_url_https": "https://example.com/video.mp4",
                        "type": "video",
                    },
                ],
            },
        }

        # noinspection PyUnresolvedReferences
        # Call the private method directly for testing
        result = fetcher._TwitterStatusFetcher__resolve_photo_contents(tweet_with_photos, "Some context")

        expected_result = (
            "---\n"
            "Photo [1]: https://example.com/photo1.jpg\n"  # Index starts from 1
            "A beautiful landscape.\n"
            "---\n"
            "Photo [2]: https://example.com/photo2.png\n"  # Index starts from 1
            "A beautiful landscape."
        )
        self.assertEqual(result, expected_result)

        # Check if the analyzer was called with the correct arguments
        mock_analyzer.assert_any_call(
            job_id = "tweet-123456789",
            image_mime_type = "image/jpeg",  # Based on .jpg extension
            open_ai_api_key = config.open_ai_token,
            image_url = "https://example.com/photo1.jpg",
            additional_context = "[[ Tweet / X Post ]]\n\nSome context",
        )
        mock_analyzer.assert_any_call(
            job_id = "tweet-123456789",
            image_mime_type = "image/jpeg",  # Based on .jpg extension
            open_ai_api_key = config.open_ai_token,
            image_url = "https://example.com/photo1.jpg",
            additional_context = "[[ Tweet / X Post ]]\n\nSome context",
        )
        mock_analyzer.assert_any_call(
            job_id = "tweet-123456789",
            image_mime_type = "image/png",  # Based on .png extension
            open_ai_api_key = config.open_ai_token,
            image_url = "https://example.com/photo2.png",
            additional_context = "[[ Tweet / X Post ]]\n\nSome context",
        )

    def test_format_tweet_content_handles_missing_data(self):
        fetcher = TwitterStatusFetcher("123456789", self.mock_cache_crud)
        response = {
            "data": {
                "data": {
                    "tweetResult": {"result": {"core": {"user_results": {"result": {"legacy": {}}}}, "legacy": {}}},
                },
            },
        }
        # noinspection PyUnresolvedReferences
        result = fetcher._TwitterStatusFetcher__resolve_content(response)
        expected_result = "@anonymous · <Anonymous>\n[Locale:en] Bio: \"<No bio>\"\n```\n<This tweet has no text>\n```"
        self.assertEqual(result, expected_result)
