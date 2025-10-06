import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from pydantic import SecretStr
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from api.auth import (
    create_jwt_token,
    get_chat_type_from_jwt,
    get_user_id_from_jwt,
    verify_api_key,
    verify_jwt_credentials,
    verify_telegram_auth_key,
    verify_whatsapp_signature,
    verify_whatsapp_webhook_challenge,
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
        mock_config.api_key = SecretStr("VALI-DKEY")
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
        mock_config.telegram_auth_key = SecretStr("VALI-DKEY")
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
        mock_config.jwt_secret_key = SecretStr("secret")
        expected_payload = {"sub": "1234"}
        mock_jwt.decode.return_value = expected_payload

        result = verify_jwt_credentials(HTTPAuthorizationCredentials(scheme = "Bearer", credentials = "valid-token"))
        self.assertEqual(result, expected_payload)

    def test_create_jwt_token(self):
        payload = {"sub": "1234"}
        encoded_token = create_jwt_token(payload, expires_in_minutes = 1)
        decoded_token = jwt.decode(encoded_token, config.jwt_secret_key.get_secret_value())
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

    def test_get_chat_type_from_jwt_valid(self):
        claims = {"platform": "telegram"}
        chat_type = get_chat_type_from_jwt(claims)
        self.assertEqual(chat_type, "telegram")

    def test_get_chat_type_from_jwt_none_claims(self):
        chat_type = get_chat_type_from_jwt(None)
        self.assertIsNone(chat_type)

    def test_get_chat_type_from_jwt_missing_platform(self):
        claims = {"sub": "user-123"}
        chat_type = get_chat_type_from_jwt(claims)
        self.assertIsNone(chat_type)

    @patch("api.auth.config")
    def test_whatsapp_webhook_challenge_success(self, mock_config: MagicMock):
        mock_config.whatsapp_must_auth = True
        mock_config.whatsapp_auth_key = SecretStr("test-token")
        challenge = verify_whatsapp_webhook_challenge("subscribe", "test-challenge", "test-token")
        self.assertEqual(challenge, "test-challenge")

    @patch("api.auth.config")
    def test_whatsapp_webhook_challenge_invalid_token(self, mock_config: MagicMock):
        mock_config.whatsapp_must_auth = True
        mock_config.whatsapp_auth_key = SecretStr("correct-token")
        with self.assertRaises(HTTPException) as context:
            verify_whatsapp_webhook_challenge("subscribe", "test-challenge", "wrong-token")
        self.assertEqual(context.exception.status_code, HTTP_403_FORBIDDEN)
        self.assertEqual(context.exception.detail, "Webhook verification failed")

    @patch("api.auth.config")
    def test_whatsapp_webhook_challenge_invalid_mode(self, mock_config: MagicMock):
        mock_config.whatsapp_must_auth = True
        mock_config.whatsapp_auth_key = SecretStr("test-token")
        with self.assertRaises(HTTPException) as context:
            verify_whatsapp_webhook_challenge("unsubscribe", "test-challenge", "test-token")
        self.assertEqual(context.exception.status_code, HTTP_403_FORBIDDEN)
        self.assertEqual(context.exception.detail, "Webhook verification failed")

    def test_whatsapp_webhook_challenge_auth_disabled(self):
        challenge = verify_whatsapp_webhook_challenge("subscribe", "test-challenge", "any-token")
        self.assertEqual(challenge, "test-challenge")

    @patch("api.auth.config")
    def test_whatsapp_signature_verification_success(self, mock_config: MagicMock):
        import hashlib
        import hmac
        mock_config.whatsapp_must_auth = True
        mock_config.whatsapp_app_secret = SecretStr("test-secret")
        payload = b'{"test": "data"}'
        signature = hmac.new(b"test-secret", payload, hashlib.sha256).hexdigest()
        verify_whatsapp_signature(payload, f"sha256={signature}")

    @patch("api.auth.config")
    def test_whatsapp_signature_verification_invalid_signature(self, mock_config: MagicMock):
        mock_config.whatsapp_must_auth = True
        mock_config.whatsapp_app_secret = SecretStr("test-secret")
        payload = b'{"test": "data"}'
        with self.assertRaises(HTTPException) as context:
            verify_whatsapp_signature(payload, "sha256=wrong-signature")
        self.assertEqual(context.exception.status_code, HTTP_403_FORBIDDEN)
        self.assertEqual(context.exception.detail, "Invalid signature")

    @patch("api.auth.config")
    def test_whatsapp_signature_verification_missing_header(self, mock_config: MagicMock):
        mock_config.whatsapp_must_auth = True
        payload = b'{"test": "data"}'
        with self.assertRaises(HTTPException) as context:
            verify_whatsapp_signature(payload, None)
        self.assertEqual(context.exception.status_code, HTTP_403_FORBIDDEN)
        self.assertEqual(context.exception.detail, "Missing signature header")

    @patch("api.auth.config")
    def test_whatsapp_signature_verification_invalid_format(self, mock_config: MagicMock):
        mock_config.whatsapp_must_auth = True
        payload = b'{"test": "data"}'
        with self.assertRaises(HTTPException) as context:
            verify_whatsapp_signature(payload, "invalid-format")
        self.assertEqual(context.exception.status_code, HTTP_403_FORBIDDEN)
        self.assertEqual(context.exception.detail, "Invalid signature format")

    def test_whatsapp_signature_verification_auth_disabled(self):
        payload = b'{"test": "data"}'
        verify_whatsapp_signature(payload, None)
