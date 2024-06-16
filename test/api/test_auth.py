import unittest
from unittest.mock import patch, MagicMock

from fastapi import HTTPException
from starlette.status import HTTP_403_FORBIDDEN

from api.auth import verify_api_key


class GetApiKeyTest(unittest.TestCase):

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

    @patch("api.auth.config")
    def test_valid_api_key(self, mock_config: MagicMock):
        mock_config.api_key = "VALI-DKEY"
        api_key = verify_api_key("VALI-DKEY")
        self.assertEqual(api_key, "VALI-DKEY")
