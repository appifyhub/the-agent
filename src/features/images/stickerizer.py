import base64
import os
from urllib.parse import urlparse

import replicate
import requests
from httpx import Timeout
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from replicate import Client

from features.ai_tools.external_ai_tool_library import CLAUDE_3_5_HAIKU, IMAGE_TO_STICKER
from features.chat.supported_files import KNOWN_IMAGE_FORMATS
from features.prompting import prompt_library
from util.config import config
from util.functions import first_key_with_value
from util.safe_printer_mixin import SafePrinterMixin

BOOT_AND_RUN_TIMEOUT_S = 180


# Not tested as it's just a proxy
class Stickerizer(SafePrinterMixin):
    __image_url: str
    __mime_type: str | None
    __face_name: str | None
    __operation_guidance: str | None
    __replicate: Client
    __copywriter: BaseChatModel

    def __init__(
        self,
        image_url: str,
        replicate_api_key: str,
        anthropic_api_key: str,
        face_name: str | None = None,
        operation_guidance: str | None = None,
        mime_type: str | None = None,
    ):
        super().__init__(config.verbose)
        self.__image_url = image_url
        self.__mime_type = mime_type
        self.__face_name = face_name
        self.__operation_guidance = operation_guidance
        self.__replicate = replicate.Client(
            api_token = replicate_api_key,
            timeout = Timeout(BOOT_AND_RUN_TIMEOUT_S),
        )
        # noinspection PyArgumentList
        self.__copywriter = ChatAnthropic(
            model_name = CLAUDE_3_5_HAIKU.id,
            temperature = 1.0,
            max_tokens = 200,
            timeout = float(config.web_timeout_s),
            max_retries = config.web_retries,
            api_key = anthropic_api_key,
        )

    def execute(self) -> str | None:
        self.sprint("Starting stickerization")
        try:
            response = requests.get(self.__image_url)
            content_b64 = base64.b64encode(response.content).decode("utf-8")
            response_mime_type = response.headers.get("Content-Type", "").split(";")[0]
            mime_type_forced = self.__mime_type or response_mime_type or "image/jpeg"
            image_encoded_b64 = f"data:{mime_type_forced};base64,{content_b64}"
            prompt = ", ".join(filter(None, [self.__face_name, self.__resolve_emotion_guidance()]))
            input_data = {
                "image": image_encoded_b64,
                "prompt": prompt,
                "steps": 30,
                "prompt_strength": 4.5,
                "instant_id_strength": 0.7,
                "upscale": True,
                "upscale_steps": 10,
            }

            result = self.__replicate.run(IMAGE_TO_STICKER.id, input = input_data)
            if not result:
                self.sprint("Failed to stickerize (no output URL)")
                return None
            self.sprint("Stickerization successful")
            # noinspection PyUnresolvedReferences
            return str(result[1])  # first link has a background, second is transparent
        except Exception as e:
            self.sprint("Error stickerizing", e)
            return None

    def __resolve_emotion_guidance(self) -> str | None:
        self.sprint("Resolving emotion guidance")
        if not self.__operation_guidance:
            return None
        answer = self.__copywriter.invoke(
            [
                SystemMessage(prompt_library.emotion_resolver),
                HumanMessage(self.__operation_guidance),
            ]
        )
        if not isinstance(answer, AIMessage):
            raise AssertionError(f"Received a non-AI message from the model: {answer}")
        if not answer.content or not isinstance(answer.content, str):
            raise AssertionError(f"Received an unexpected content from the model: {answer}")
        emotion = str(answer.content).lower().strip()
        if emotion == "neutral":
            return None
        return f"{str(answer.content)} person"

    def __get_suffix(self) -> str:
        # check if the URL already contains a file extension
        url_path = urlparse(self.__image_url).path
        file_with_extension = os.path.splitext(url_path)[1]
        if file_with_extension:
            return f".{file_with_extension.lstrip(".")}"
        # if no extension in URL, use MIME type to determine extension
        if self.__mime_type:
            return first_key_with_value(KNOWN_IMAGE_FORMATS, self.__mime_type)
        return ""
