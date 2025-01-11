import io
import os
from urllib.parse import urlparse

import requests
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from openai import OpenAI
from pydub import AudioSegment

from features.chat.supported_files import (
    SUPPORTED_AUDIO_FORMATS,
    EXTENSION_FORMAT_MAP,
    TARGET_AUDIO_FORMAT,
)
from features.prompting import prompt_library
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

TRANSCRIBER_AUDIO_MODEL_NAME = "whisper-1"
COPYWRITER_OPEN_AI_MODEL = "gpt-4o-mini"
COPYWRITER_OPEN_AI_TEMPERATURE = 0.4
COPYWRITER_OPEN_AI_MAX_TOKENS = 4096


class AudioTranscriber(SafePrinterMixin):
    __job_id: str
    __audio_content: bytes
    __extension: str
    __copywriter_messages: list[BaseMessage]
    __copywriter: BaseChatModel
    __transcriber: OpenAI

    def __init__(
        self,
        job_id: str,
        audio_url: str,
        open_ai_api_key: str,
        def_extension: str | None = None,
        audio_content: bytes | None = None,
        language_name: str | None = None,
        language_iso_code: str | None = None,
    ):
        super().__init__(config.verbose)
        self.__job_id = job_id
        self.__resolve_extension(audio_url, def_extension)
        self.__validate_content(audio_url, audio_content)
        self.__transcriber = OpenAI(api_key = open_ai_api_key)
        copywriter_prompt = prompt_library.translator_on_response(
            base_prompt = prompt_library.transcription_copywriter,
            language_name = language_name,
            language_iso_code = language_iso_code,
        )
        self.__copywriter_messages = []
        self.__copywriter_messages.append(SystemMessage(copywriter_prompt))
        # noinspection PyArgumentList
        self.__copywriter = ChatOpenAI(
            model = COPYWRITER_OPEN_AI_MODEL,
            temperature = COPYWRITER_OPEN_AI_TEMPERATURE,
            max_tokens = COPYWRITER_OPEN_AI_MAX_TOKENS,
            timeout = float(config.web_timeout_s) * 2,  # increase timeout for transcription copywriting
            max_retries = config.web_retries,
            api_key = str(open_ai_api_key),
        )

    def __validate_content(self, audio_url: str, audio_content: bytes | None):
        self.sprint(f"Fetching and validating audio from URL '{audio_url}'")
        self.__audio_content = audio_content or requests.get(audio_url).content

        if self.__extension not in SUPPORTED_AUDIO_FORMATS.keys():
            self.sprint(f"  Unsupported audio format: '.{self.__extension}'")
            convertible_format = EXTENSION_FORMAT_MAP.get(self.__extension)
            if convertible_format:
                self.__audio_content = self.__convert_to_wav(convertible_format)
                self.__extension = TARGET_AUDIO_FORMAT
        self.sprint(f"  Audio contents fetched. Extension: '.{self.__extension}'")
        self.sprint(f"  Audio content size: {len(self.__audio_content) / 1024:.2f} KB")

    def __resolve_extension(self, audio_url: str, def_extension: str | None):
        self.sprint(f"Extracting audio extension from {audio_url}")
        path = urlparse(audio_url).path
        self.__extension = os.path.splitext(path)[1][1:].lower()
        if self.__extension:
            self.sprint(f"  Extracted extension: '.{self.__extension}'")
            return
        assumed_extension = def_extension or TARGET_AUDIO_FORMAT
        self.sprint(f"  No extension found, assuming '.{assumed_extension}'...")
        self.__extension = assumed_extension

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
            # first resolve the transcription
            buffer = io.BytesIO(self.__audio_content)
            buffer.name = f"audio.{self.__extension}"
            transcript = self.__transcriber.audio.transcriptions.create(
                model = TRANSCRIBER_AUDIO_MODEL_NAME,
                file = buffer,
                response_format = "text",
            )
            raw_transcription = str(transcript)

            # then fix the transcription using the copywriter
            self.__copywriter_messages.append(HumanMessage(raw_transcription))
            answer = self.__copywriter.invoke(self.__copywriter_messages)
            if not isinstance(answer, AIMessage):
                raise AssertionError(f"Received a non-AI message from the model: {answer}")
            if not answer.content or not isinstance(answer.content, str):
                raise AssertionError(f"Received an unexpected content from the model: {answer}")
            transcription = str(answer.content)
            self.sprint(f"Raw transcription: `{transcription}`")
            return transcription
        except Exception as e:
            self.sprint("Audio analysis failed", e)
            return None
