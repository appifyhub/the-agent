import io
import unittest
from unittest.mock import patch, MagicMock, ANY, call

import requests_mock

from features.audio.audio_transcriber import AudioTranscriber, SUPPORTED_AUDIO_FORMATS


class AudioTranscriberTest(unittest.TestCase):

    def setUp(self):
        self.job_id = "test_job"
        self.audio_url = "https://example.com/audio.mp3"
        self.open_ai_api_key = "test_key"

    @requests_mock.Mocker()
    def test_init(self, m):
        m.get(self.audio_url, content = b"audio_content")
        transcriber = AudioTranscriber(self.job_id, self.audio_url, self.open_ai_api_key)
        self.assertIsInstance(transcriber, AudioTranscriber)

    @requests_mock.Mocker()
    def test_validate_content_supported_format(self, m):
        m.get(self.audio_url, content = b"audio_content")
        transcriber = AudioTranscriber(self.job_id, self.audio_url, self.open_ai_api_key)
        # noinspection PyUnresolvedReferences
        self.assertEqual(transcriber._AudioTranscriber__extension, "mp3")

    @requests_mock.Mocker()
    def test_validate_content_unsupported_format(self, m):
        unsupported_url = "https://example.com/audio.unsupported"
        m.get(unsupported_url, content = b"audio_content")
        transcriber = AudioTranscriber(self.job_id, unsupported_url, self.open_ai_api_key)
        # noinspection PyUnresolvedReferences
        self.assertEqual(transcriber._AudioTranscriber__extension, "unsupported")
        # noinspection PyUnresolvedReferences
        self.assertNotIn(transcriber._AudioTranscriber__extension, SUPPORTED_AUDIO_FORMATS)

    @requests_mock.Mocker()
    @patch("features.audio.audio_transcriber.AudioTranscriber._AudioTranscriber__convert_to_wav")
    def test_validate_content_ogg_format(self, m, mock_convert):
        ogg_url = "https://example.com/audio.ogg"
        m.get(ogg_url, content = b"audio_content")
        mock_convert.return_value = b"converted_audio_content"
        transcriber = AudioTranscriber(self.job_id, ogg_url, self.open_ai_api_key)
        # noinspection PyUnresolvedReferences
        self.assertEqual(transcriber._AudioTranscriber__extension, "wav")

    @requests_mock.Mocker()
    def test_resolve_extension_with_extension(self, m):
        m.get(self.audio_url, content = b"audio_content")
        transcriber = AudioTranscriber(self.job_id, self.audio_url, self.open_ai_api_key)
        # noinspection PyUnresolvedReferences
        transcriber._AudioTranscriber__resolve_extension(self.audio_url, "wav")
        # noinspection PyUnresolvedReferences
        self.assertEqual(transcriber._AudioTranscriber__extension, "mp3")

    @requests_mock.Mocker()
    def test_resolve_extension_without_extension(self, m):
        url_without_extension = "https://example.com/audio"
        m.get(url_without_extension, content = b"audio_content")
        transcriber = AudioTranscriber(self.job_id, url_without_extension, self.open_ai_api_key)
        # noinspection PyUnresolvedReferences
        transcriber._AudioTranscriber__resolve_extension(url_without_extension, "wav")
        # noinspection PyUnresolvedReferences
        self.assertEqual(transcriber._AudioTranscriber__extension, "wav")

    @patch("features.audio.audio_transcriber.AudioSegment")
    @patch("features.audio.audio_transcriber.requests.get")
    def test_convert_to_wav(self, mock_get, mock_audio_segment):
        # Mock the network request
        mock_response = MagicMock()
        mock_response.content = b"network_fetched_content"
        mock_get.return_value = mock_response

        mock_audio = MagicMock()
        mock_audio_segment.from_file.return_value = mock_audio
        mock_buffer = io.BytesIO(b"mocked wav data")
        mock_audio.export.return_value = mock_buffer

        self.job_id = "test_job"
        self.audio_url = "https://example.com/audio.ogg"
        self.open_ai_api_key = "test_key"

        transcriber = AudioTranscriber(self.job_id, self.audio_url, self.open_ai_api_key)
        original_content = b"audio_content"
        transcriber._AudioTranscriber__audio_content = original_content
        # noinspection PyUnresolvedReferences
        result = transcriber._AudioTranscriber__convert_to_wav("ogg")

        self.assertEqual(result, b'')
        expected_calls = [
            call(ANY, format = 'ogg'),
            call(ANY, format = 'ogg')
        ]
        mock_audio_segment.from_file.assert_has_calls(expected_calls, any_order = True)
        self.assertEqual(mock_audio_segment.from_file.call_count, 2)

        last_call_args = mock_audio_segment.from_file.call_args_list[-1]
        self.assertEqual(last_call_args[0][0].getvalue(), original_content)

        mock_audio.export.assert_called_with(ANY, format = "wav")
        self.assertEqual(transcriber._AudioTranscriber__audio_content, original_content)
        self.assertEqual(mock_buffer.getvalue(), b"mocked wav data")

    @requests_mock.Mocker()
    @patch("features.audio.audio_transcriber.OpenAI")
    def test_execute_success(self, m, mock_openai):
        m.get(self.audio_url, content = b"audio_content")
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.audio.transcriptions.create.return_value = "Transcribed text"

        transcriber = AudioTranscriber(self.job_id, self.audio_url, self.open_ai_api_key)
        result = transcriber.execute()

        self.assertEqual(result, "Transcribed text")
        mock_client.audio.transcriptions.create.assert_called_once()

    @requests_mock.Mocker()
    @patch("features.audio.audio_transcriber.OpenAI")
    def test_execute_failure(self, m, mock_openai):
        m.get(self.audio_url, content = b"audio_content")
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.audio.transcriptions.create.side_effect = Exception("API error")

        transcriber = AudioTranscriber(self.job_id, self.audio_url, self.open_ai_api_key)
        result = transcriber.execute()

        self.assertIsNone(result)
