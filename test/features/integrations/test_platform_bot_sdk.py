import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from db.model.chat_config import ChatConfigDB
from di.di import DI
from features.integrations.platform_bot_sdk import PlatformBotSDK


def _make_di() -> DI:
    di = Mock(spec = DI)
    di.require_invoker_chat_type.return_value = ChatConfigDB.ChatType.telegram
    di.require_invoker_chat.return_value = SimpleNamespace(media_mode = ChatConfigDB.MediaMode.photo)
    di.telegram_bot_sdk = Mock()
    di.telegram_bot_sdk.send_photo = Mock(return_value = "sent")
    di.whatsapp_bot_sdk = Mock()
    di.image_uploader = MagicMock()
    return di


def _mock_response(content_length: int | None = None, body: bytes = b"") -> Mock:
    resp = Mock()
    resp.headers = {}
    if content_length is not None:
        resp.headers["Content-Length"] = str(content_length)
    resp.iter_content.return_value = [body]
    resp.raise_for_status = Mock()
    resp.__enter__ = Mock(return_value = resp)
    resp.__exit__ = Mock(return_value = False)
    return resp


def _make_temp_file(content: bytes = b"data") -> str:
    tmp = tempfile.NamedTemporaryFile(delete = False, suffix = ".png")
    tmp.write(content)
    tmp.flush()
    tmp.close()
    return tmp.name


class PlatformBotSDKTest(unittest.TestCase):

    def test_send_photo_resizes_and_uploads(self):
        """Test that send_photo resizes large images and uploads them"""
        di = _make_di()
        resized_path = _make_temp_file(b"resized")
        uploader = Mock()
        uploader.execute.return_value = "uploaded-url"
        di.image_uploader.return_value = uploader
        sdk = PlatformBotSDK(di = di)
        with patch("features.integrations.platform_bot_sdk.requests.head") as mock_head, \
                patch("features.integrations.platform_bot_sdk.requests.get") as mock_get, \
                patch("features.integrations.platform_bot_sdk.resize_file") as mock_resize:
            mock_head.return_value = _mock_response(content_length = 6 * 1024 * 1024)
            mock_get.return_value = _mock_response(body = b"x" * (6 * 1024 * 1024))
            mock_resize.return_value = resized_path
            result = sdk.send_photo(chat_id = 1, photo_url = "http://example.com/img.png")
        mock_resize.assert_called_once()
        di.telegram_bot_sdk.send_photo.assert_called_once_with(1, "uploaded-url", None)
        self.assertEqual(result, "sent")

    def test_send_photo_head_failure_still_resizes_and_uploads(self):
        """Test that send_photo handles HEAD request failure gracefully"""
        di = _make_di()
        resized_path = _make_temp_file(b"resized")
        uploader = Mock()
        uploader.execute.return_value = "uploaded-url"
        di.image_uploader.return_value = uploader
        sdk = PlatformBotSDK(di = di)
        with patch("features.integrations.platform_bot_sdk.requests.head") as mock_head, \
                patch("features.integrations.platform_bot_sdk.requests.get") as mock_get, \
                patch("features.integrations.platform_bot_sdk.resize_file") as mock_resize:
            mock_head.side_effect = Exception("head failed")
            mock_get.return_value = _mock_response(body = b"x" * (6 * 1024 * 1024))
            mock_resize.return_value = resized_path
            result = sdk.send_photo(chat_id = 1, photo_url = "http://example.com/img.png")
        mock_resize.assert_called_once()
        di.telegram_bot_sdk.send_photo.assert_called_once_with(1, "uploaded-url", None)
        self.assertEqual(result, "sent")

    def test_send_photo_resize_failure_falls_back_to_original(self):
        """Test that send_photo uses original URL if resizing fails"""
        di = _make_di()
        uploader = Mock()
        uploader.execute.return_value = "uploaded-url"
        di.image_uploader.return_value = uploader
        sdk = PlatformBotSDK(di = di)
        with patch("features.integrations.platform_bot_sdk.requests.head") as mock_head, \
                patch("features.integrations.platform_bot_sdk.requests.get") as mock_get, \
                patch("features.integrations.platform_bot_sdk.resize_file") as mock_resize:
            mock_head.return_value = _mock_response(content_length = 6 * 1024 * 1024)
            mock_get.return_value = _mock_response(body = b"x" * (6 * 1024 * 1024))
            mock_resize.side_effect = Exception("resize failed")
            result = sdk.send_photo(chat_id = 1, photo_url = "http://example.com/img.png")
        di.telegram_bot_sdk.send_photo.assert_called_once_with(1, "http://example.com/img.png", None)
        self.assertEqual(result, "sent")

    def test_send_photo_uploader_failure_falls_back_to_original(self):
        """Test that send_photo uses original URL if upload fails"""
        di = _make_di()
        resized_path = _make_temp_file(b"resized")
        uploader = Mock()
        uploader.execute.side_effect = Exception("upload failed")
        di.image_uploader.return_value = uploader
        sdk = PlatformBotSDK(di = di)
        with patch("features.integrations.platform_bot_sdk.requests.head") as mock_head, \
                patch("features.integrations.platform_bot_sdk.requests.get") as mock_get, \
                patch("features.integrations.platform_bot_sdk.resize_file") as mock_resize:
            mock_head.return_value = _mock_response(content_length = 6 * 1024 * 1024)
            mock_get.return_value = _mock_response(body = b"x" * (6 * 1024 * 1024))
            mock_resize.return_value = resized_path
            result = sdk.send_photo(chat_id = 1, photo_url = "http://example.com/img.png")
        di.telegram_bot_sdk.send_photo.assert_called_once_with(1, "http://example.com/img.png", None)
        self.assertEqual(result, "sent")


class TempFileBehaviorTest(unittest.TestCase):

    def test_named_temporary_file_deleted_manually(self):
        with tempfile.NamedTemporaryFile(delete = False) as tmp:
            path = tmp.name
            tmp.write(b"data")
        self.assertTrue(os.path.exists(path))
        os.unlink(path)
        self.assertFalse(os.path.exists(path))
