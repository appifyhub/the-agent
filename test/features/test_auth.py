import unittest
from unittest.mock import patch, MagicMock

from fastapi import HTTPException
from starlette.status import HTTP_403_FORBIDDEN

from features.auth import verify_api_key, verify_telegram_auth_key


class AuthTest(unittest.TestCase):

    def test_missing_api_key(self):
        with self.assertRaises(HTTPException) as context:
            # server will break the rule too, so:
            # noinspection PyTypeChecker
            verify_api_key(None)
        self.assertEqual(context.exception.status_code, HTTP_403_FORBIDDEN)
        self.assertEqual(context.exception.detail, "Could not validate the API key")

    def test_invalid_api_key(self):
        with self.assertRaises(HTTPException) as context:
            verify_api_key("NOTA-VALI-DKEY")
        self.assertEqual(context.exception.status_code, HTTP_403_FORBIDDEN)
        self.assertEqual(context.exception.detail, "Could not validate the API key")

    @patch("features.auth.config")
    def test_valid_api_key(self, mock_config: MagicMock):
        mock_config.api_key = "VALI-DKEY"
        api_key = verify_api_key("VALI-DKEY")
        self.assertEqual(api_key, "VALI-DKEY")

    @patch("features.auth.config")
    def test_missing_telegram_auth_key(self, mock_config: MagicMock):
        mock_config.telegram_must_auth = True
        with self.assertRaises(HTTPException) as context:
            # server will break the rule too, so:
            # noinspection PyTypeChecker
            verify_telegram_auth_key(None)
        self.assertEqual(context.exception.status_code, HTTP_403_FORBIDDEN)
        self.assertEqual(context.exception.detail, "Could not validate the Telegram auth token")

    @patch("features.auth.config")
    def test_invalid_telegram_auth_key(self, mock_config: MagicMock):
        mock_config.telegram_must_auth = True
        with self.assertRaises(HTTPException) as context:
            verify_telegram_auth_key("NOTA-VALI-DKEY")
        self.assertEqual(context.exception.status_code, HTTP_403_FORBIDDEN)
        self.assertEqual(context.exception.detail, "Could not validate the Telegram auth token")

    def test_disabled_telegram_auth_key(self):
        auth_key = verify_telegram_auth_key("")
        self.assertEqual(auth_key, "")

    @patch("features.auth.config")
    def test_valid_telegram_auth_key(self, mock_config: MagicMock):
        mock_config.telegram_must_auth = True
        mock_config.telegram_auth_key = "VALI-DKEY"
        auth_key = verify_telegram_auth_key("VALI-DKEY")
        self.assertEqual(auth_key, "VALI-DKEY")
