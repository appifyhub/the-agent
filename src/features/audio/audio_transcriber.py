import io
import os
from urllib.parse import urlparse

import requests
from openai import OpenAI
from pydub import AudioSegment

from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

OPEN_AI_MODEL_NAME = "whisper-1"
SUPPORTED_AUDIO_FORMATS = {"mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"}


class AudioTranscriber(SafePrinterMixin):
    __job_id: str
    __client: OpenAI
    __audio_content: bytes
    __extension: str

    def __init__(self, job_id: str, audio_url: str, open_ai_api_key: str, def_extension: str = "wav"):
        super().__init__(config.verbose)
        self.__job_id = job_id
        self.__client = OpenAI(api_key = open_ai_api_key)
        self.__validate_content(audio_url, def_extension)

    def __validate_content(self, audio_url: str, def_extension: str):
        self.sprint(f"Fetching and validating audio from URL '{audio_url}'")
        self.__resolve_extension(audio_url, def_extension)
        self.__audio_content = requests.get(audio_url).content

        if self.__extension not in SUPPORTED_AUDIO_FORMATS:
            self.sprint(f"  Unsupported audio format: '.{self.__extension}'")
            # OGA/OGG audio, possible voice recording (we can convert)
            if self.__extension == "oga" or self.__extension == "ogg":
                self.__audio_content = self.__convert_to_wav("ogg")
                self.__extension = "wav"
        self.sprint(f"  Audio contents fetched. Extension: '.{self.__extension}'")
        self.sprint(f"  Audio content size: {len(self.__audio_content) / 1024:.2f} KB")

    def __resolve_extension(self, audio_url: str, def_extension: str):
        self.sprint(f"Extracting audio extension from {audio_url}")
        path = urlparse(audio_url).path
        self.__extension = os.path.splitext(path)[1][1:].lower()
        if self.__extension:
            self.sprint(f"  Extracted extension: '.{self.__extension}'")
            return
        self.sprint(f"  No extension found, assuming '.{def_extension}'...")
        self.__extension = def_extension

    def __convert_to_wav(self, source_format: str) -> bytes:
        self.sprint(f"Converting {source_format} to wav")
        buffer = io.BytesIO(self.__audio_content)
        audio = AudioSegment.from_file(buffer, format = source_format)
        new_buffer = io.BytesIO()
        audio.export(new_buffer, format = "wav")
        return new_buffer.getvalue()

    def execute(self) -> str | None:
        self.sprint(f"Starting audio analysis for job '{self.__job_id}'")
        try:
            buffer = io.BytesIO(self.__audio_content)
            buffer.name = f"audio.{self.__extension}"
            transcript = self.__client.audio.transcriptions.create(
                model = OPEN_AI_MODEL_NAME,
                file = buffer,
                response_format = "text",
            )
            return str(transcript)
        except Exception as e:
            self.sprint("Audio analysis failed", e)
            return None
