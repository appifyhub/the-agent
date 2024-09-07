import unittest
from unittest.mock import MagicMock, patch

from features.web_browsing.twitter_utils import resolve_tweet_id
from util.config import config


class TwitterUtilsTest(unittest.TestCase):

    def setUp(self):
        config.web_timeout_s = 0

    @patch("requests.get")
    def test_detect_tweet_id(self, mock_get):
        mock_response = MagicMock()
        mock_response.url = "https://twitter.com/username/status/123456789"
        mock_get.return_value = mock_response
        test_cases = [
            ("https://twitter.com/username/status/123456789", "123456789"),
            ("https://x.com/username/status/123456789", "123456789"),
            ("https://twitter.com/username/status/123456789?s=20", "123456789"),
            ("https://t.co/abcdefg", "123456789"),
            ("https://example.com", None),
        ]
        for url, expected_id in test_cases:
            with self.subTest(url = url):
                self.assertEqual(resolve_tweet_id(url), expected_id)
        mock_get.assert_called_once_with("https://t.co/abcdefg", timeout = config.web_timeout_s)
