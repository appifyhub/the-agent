import io
import os
from urllib.parse import urlparse

import requests
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from openai import OpenAI
from pydub import AudioSegment

from di.di import DI
from features.chat.supported_files import (
    EXTENSION_FORMAT_MAP,
    SUPPORTED_AUDIO_FORMATS,
    TARGET_AUDIO_FORMAT,
)
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import CLAUDE_3_5_HAIKU, WHISPER_1
from features.external_tools.tool_choice_resolver import ConfiguredTool
from features.prompting import prompt_library
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


# Not tested as it's just a proxy
class AudioTranscriber(SafePrinterMixin):
    DEFAULT_TRANSCRIBER_TOOL: ExternalTool = WHISPER_1
    TRANSCRIBER_TOOL_TYPE: ToolType = ToolType.hearing
    DEFAULT_COPYWRITER_TOOL: ExternalTool = CLAUDE_3_5_HAIKU
    COPYWRITER_TOOL_TYPE: ToolType = ToolType.copywriting

    __job_id: str
    __audio_content: bytes
    __extension: str
    __transcriber_tool: ConfiguredTool
    __copywriter_tool: ConfiguredTool
    __language_name: str | None
    __language_iso_code: str | None
    __transcriber: OpenAI
    __copywriter: BaseChatModel
    __di: DI

    def __init__(
        self,
        job_id: str,
        audio_url: str,
        transcriber_tool: ConfiguredTool,
        copywriter_tool: ConfiguredTool,
        di: DI,
        def_extension: str | None = None,
        audio_content: bytes | None = None,
        language_name: str | None = None,
        language_iso_code: str | None = None,
    ):
        super().__init__(config.verbose)
        self.__job_id = job_id
        self.__resolve_extension(audio_url, def_extension)
        self.__validate_content(audio_url, audio_content)
        self.__transcriber_tool = transcriber_tool
        self.__copywriter_tool = copywriter_tool
        self.__language_name = language_name
        self.__language_iso_code = language_iso_code
        _, transcriber_token, _ = transcriber_tool
        self.__transcriber = OpenAI(api_key = transcriber_token.get_secret_value())
        self.__copywriter = di.chat_langchain_model(copywriter_tool)
        self.__di = di

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
            transcriber_tool, _, _ = self.__transcriber_tool
            transcript = self.__transcriber.audio.transcriptions.create(
                model = transcriber_tool.id,
                file = buffer,
                response_format = "text",
            )
            raw_transcription = str(transcript)

            # then fix the transcription using the copywriter
            copywriter_prompt = prompt_library.translator_on_response(
                base_prompt = prompt_library.transcription_copywriter,
                language_name = self.__language_name,
                language_iso_code = self.__language_iso_code,
            )
            copywriter_messages = [SystemMessage(copywriter_prompt), HumanMessage(raw_transcription)]
            answer = self.__copywriter.invoke(copywriter_messages)
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
