import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from api.auth import (
    create_jwt_token,
    get_user_id_from_jwt,
    verify_api_key,
    verify_jwt_credentials,
    verify_telegram_auth_key,
)
from util.config import config


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

    @patch("api.auth.config")
    def test_valid_api_key(self, mock_config: MagicMock):
        mock_config.api_key = "VALI-DKEY"
        api_key = verify_api_key("VALI-DKEY")
        self.assertEqual(api_key, "VALI-DKEY")

    @patch("api.auth.config")
    def test_missing_telegram_auth_key(self, mock_config: MagicMock):
        mock_config.telegram_must_auth = True
        with self.assertRaises(HTTPException) as context:
            # server will break the rule too, so:
            # noinspection PyTypeChecker
            verify_telegram_auth_key(None)
        self.assertEqual(context.exception.status_code, HTTP_403_FORBIDDEN)
        self.assertEqual(context.exception.detail, "Could not validate the Telegram auth token")

    @patch("api.auth.config")
    def test_invalid_telegram_auth_key(self, mock_config: MagicMock):
        mock_config.telegram_must_auth = True
        with self.assertRaises(HTTPException) as context:
            verify_telegram_auth_key("NOTA-VALI-DKEY")
        self.assertEqual(context.exception.status_code, HTTP_403_FORBIDDEN)
        self.assertEqual(context.exception.detail, "Could not validate the Telegram auth token")

    def test_disabled_telegram_auth_key(self):
        auth_key = verify_telegram_auth_key("")
        self.assertEqual(auth_key, "")

    @patch("api.auth.config")
    def test_valid_telegram_auth_key(self, mock_config: MagicMock):
        mock_config.telegram_must_auth = True
        mock_config.telegram_auth_key = "VALI-DKEY"
        auth_key = verify_telegram_auth_key("VALI-DKEY")
        self.assertEqual(auth_key, "VALI-DKEY")

    def test_missing_jwt_token(self):
        with self.assertRaises(HTTPException) as context:
            # noinspection PyTypeChecker
            verify_jwt_credentials(None)
        self.assertEqual(context.exception.status_code, HTTP_401_UNAUTHORIZED)
        self.assertEqual(context.exception.detail, "Could not validate access credentials")

    @patch("api.auth.jwt")
    def test_invalid_jwt_token(self, mock_jwt: MagicMock):
        mock_jwt.decode.side_effect = Exception()
        with self.assertRaises(HTTPException) as context:
            verify_jwt_credentials(HTTPAuthorizationCredentials(scheme = "Bearer", credentials = "invalid-token"))
        self.assertEqual(context.exception.status_code, HTTP_401_UNAUTHORIZED)
        self.assertEqual(context.exception.detail, "Could not validate access credentials")

    @patch("api.auth.jwt")
    @patch("api.auth.config")
    def test_valid_jwt_token(self, mock_config: MagicMock, mock_jwt: MagicMock):
        mock_config.jwt_secret_key = "secret"
        expected_payload = {"sub": "1234"}
        mock_jwt.decode.return_value = expected_payload

        result = verify_jwt_credentials(HTTPAuthorizationCredentials(scheme = "Bearer", credentials = "valid-token"))
        self.assertEqual(result, expected_payload)

    def test_create_jwt_token(self):
        payload = {"sub": "1234"}
        encoded_token = create_jwt_token(payload, expires_in_minutes = 1)
        decoded_token = jwt.decode(encoded_token, config.jwt_secret_key)
        self.assertIsNotNone(encoded_token, str)
        self.assertIsInstance(encoded_token, str)
        self.assertIsNotNone(decoded_token["exp"])
        self.assertIsNotNone(decoded_token["iat"])
        self.assertIsNotNone(decoded_token["version"])

    def test_get_user_id_from_jwt_valid(self):
        claims = {"sub": "user-123"}
        user_id = get_user_id_from_jwt(claims)
        self.assertEqual(user_id, "user-123")

    def test_get_user_id_from_jwt_empty_claims(self):
        with self.assertRaises(ValueError) as context:
            get_user_id_from_jwt({"other": "claim"})
        self.assertIn("No user ID in token", str(context.exception))

    def test_get_user_id_from_jwt_none_claims(self):
        with self.assertRaises(ValueError) as context:
            get_user_id_from_jwt(None)
        self.assertIn("Empty token", str(context.exception))

    def test_get_user_id_from_jwt_missing_sub(self):
        claims = {"not_sub": "no-user-id"}
        with self.assertRaises(ValueError) as context:
            get_user_id_from_jwt(claims)
        self.assertIn("No user ID in token", str(context.exception))
