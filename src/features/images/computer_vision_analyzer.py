from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from features.chat.supported_files import KNOWN_IMAGE_FORMATS
from features.prompting import prompt_library
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

OPEN_AI_MODEL = "gpt-4o"
OPEN_AI_TEMPERATURE = 0.5
OPEN_AI_MAX_TOKENS = 2048


class ComputerVisionAnalyzer(SafePrinterMixin):
    __job_id: str
    __messages: list[BaseMessage]
    __vision_model: BaseChatModel

    def __init__(
        self,
        job_id: str,
        image_mime_type: str,
        open_ai_api_key: str,
        image_url: str | None = None,
        image_b64: str | None = None,
        additional_context: str | None = None,
    ):
        super().__init__(config.verbose)
        self.__job_id = job_id
        if image_mime_type not in KNOWN_IMAGE_FORMATS.values():
            raise ValueError(f"Unsupported image format: {image_mime_type}")
        if image_url is not None and image_b64 is not None:
            raise ValueError("Only one of URL or Base64 value must be provided")
        if image_url is None and image_b64 is None:
            raise ValueError("Either URL or Base64 value must be provided")
        # set up LLM context
        image_content_json: dict[str, str | dict] = {"type": "image_url"}
        if image_url is not None:
            image_content_json["image_url"] = {"url": image_url}
        else:  # image_b64 is not None
            data_uri = f"data:{image_mime_type};base64,{image_b64}"
            image_content_json["image_url"] = {"url": data_uri}
        content: list[dict] = []
        if additional_context:
            content.append({"type": "text", "text": additional_context})
        content.append(image_content_json)
        self.__messages = []
        self.__messages.append(SystemMessage(prompt_library.observer_computer_vision))
        self.__messages.append(HumanMessage(content = content))
        # noinspection PyArgumentList
        self.__vision_model = ChatOpenAI(
            model = OPEN_AI_MODEL,
            temperature = OPEN_AI_TEMPERATURE,
            max_tokens = OPEN_AI_MAX_TOKENS,
            timeout = float(config.web_timeout_s),
            max_retries = config.web_retries,
            api_key = str(open_ai_api_key),
        )

    def execute(self) -> str | None:
        self.sprint(f"Starting computer vision analysis for job '{self.__job_id}'")
        try:
            answer = self.__vision_model.invoke(self.__messages)
            if not isinstance(answer, AIMessage):
                raise AssertionError(f"Received a non-AI message from the model: {answer}")
            if not answer.content or not isinstance(answer.content, str):
                raise AssertionError(f"Received an unexpected content from the model: {answer}")
            return str(answer.content)
        except Exception as e:
            self.sprint("Computer vision analysis failed", e)
            return None
