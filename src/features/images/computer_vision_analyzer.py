from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from di.di import DI
from features.chat.supported_files import KNOWN_IMAGE_FORMATS
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import GPT_4_1_MINI
from features.external_tools.tool_choice_resolver import ConfiguredTool
from features.prompting import prompt_library
from util import log


# Not tested as it's just a proxy
class ComputerVisionAnalyzer:

    DEFAULT_TOOL: ExternalTool = GPT_4_1_MINI
    TOOL_TYPE: ToolType = ToolType.vision

    error: str | None = None
    __job_id: str
    __messages: list[BaseMessage]
    __vision_model: BaseChatModel

    def __init__(
        self,
        job_id: str,
        image_mime_type: str,
        configured_tool: ConfiguredTool,
        di: DI,
        image_url: str | None = None,
        image_b64: str | None = None,
        additional_context: str | None = None,
    ):
        self.__job_id = job_id

        # validate image input parameters
        if image_mime_type not in KNOWN_IMAGE_FORMATS.values():
            raise ValueError(f"Unsupported image format: {image_mime_type}")
        if image_url is not None and image_b64 is not None:
            raise ValueError("Only one of URL or Base64 value must be provided")
        if image_url is None and image_b64 is None:
            raise ValueError("Either URL or Base64 value must be provided")

        # set up LLM image context
        image_content_json: dict[str, str | dict] = {"type": "image_url"}
        if image_url is not None:
            image_content_json["image_url"] = {"url": image_url}
        else:  # image_b64 is not None
            data_uri = f"data:{image_mime_type};base64,{image_b64}"
            image_content_json["image_url"] = {"url": data_uri}
        content: list[str | dict] = []
        if additional_context:
            content.append({"type": "text", "text": additional_context})
        content.append(image_content_json)

        # initialize the LLM
        self.__messages = []
        self.__messages.append(SystemMessage(prompt_library.observer_computer_vision))
        self.__messages.append(HumanMessage(content = content))
        self.__vision_model = di.chat_langchain_model(configured_tool)

    def execute(self) -> str | None:
        log.d(f"Starting computer vision analysis for job '{self.__job_id}'")
        self.error = None
        try:
            answer = self.__vision_model.invoke(self.__messages)
            if not isinstance(answer, AIMessage):
                raise AssertionError(f"Received a non-AI message from the model: {answer}")
            if not answer.content or not isinstance(answer.content, str):
                raise AssertionError(f"Received an unexpected content from the model: {answer}")
            return str(answer.content)
        except Exception as e:
            self.error = log.e("Computer vision analysis failed", e)
            return None
