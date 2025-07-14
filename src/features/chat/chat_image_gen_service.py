from enum import Enum

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from di.di import DI
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import CLAUDE_3_5_HAIKU
from features.external_tools.tool_choice_resolver import ConfiguredTool
from features.images.text_stable_diffusion_generator import TextStableDiffusionGenerator
from features.llm import langchain_creator
from features.prompting import prompt_library
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


class ChatImageGenService(SafePrinterMixin):
    class Result(Enum):
        success = "Success"
        failed = "Failed"

    DEFAULT_COPYWRITER_TOOL: ExternalTool = CLAUDE_3_5_HAIKU
    COPYWRITER_TOOL_TYPE: ToolType = ToolType.copywriting

    DEFAULT_IMAGE_GEN_TOOL: ExternalTool = TextStableDiffusionGenerator.DEFAULT_TOOL
    IMAGE_GEN_TOOL_TYPE: ToolType = TextStableDiffusionGenerator.TOOL_TYPE

    __llm_input: list[BaseMessage]
    __image_gen_tool: ConfiguredTool
    __copywriter: BaseChatModel
    __di: DI

    def __init__(
        self,
        raw_prompt: str,
        configured_copywriter_tool: ConfiguredTool,
        configured_image_gen_tool: ConfiguredTool,
        di: DI,
    ):
        super().__init__(config.verbose)
        self.__di = di
        self.__copywriter = langchain_creator.create(configured_copywriter_tool)
        self.__llm_input = []
        self.__llm_input.append(SystemMessage(prompt_library.generator_stable_diffusion))
        self.__llm_input.append(HumanMessage(raw_prompt))
        self.__image_gen_tool = configured_image_gen_tool

    def execute(self) -> Result:
        self.sprint(f"Generating image for chat '{self.__di.invoker_chat.chat_id}'")

        # let's correct/prettify and translate the prompt first
        try:
            self.sprint("Starting prompt correction")
            response = self.__copywriter.invoke(self.__llm_input)
            if not isinstance(response, AIMessage) or not isinstance(response.content, str):
                raise AssertionError(f"Received a complex message from LLM: {response}")
            prompt = response.content
            self.sprint(f"Finished prompt correction, new size is {len(prompt)} characters")
        except Exception as e:
            self.sprint("Error correcting raw prompt", e)
            return ChatImageGenService.Result.failed

        # let's generate the image now using the corrected prompt
        try:
            self.sprint("Starting image generation")
            image_url = self.__di.text_stable_diffusion_generator(prompt, self.__image_gen_tool).execute()
            if not image_url:
                self.sprint("Failed to generate image (no image URL found)")
                return ChatImageGenService.Result.failed
        except Exception as e:
            self.sprint("Error generating image", e)
            return ChatImageGenService.Result.failed

        # let's send the image to the chat
        try:
            self.sprint("Starting image sending")
            self.__di.telegram_bot_sdk.send_photo(self.__di.invoker_chat.chat_id, image_url)
        except Exception as e:
            self.sprint("Error sending image", e)
            return ChatImageGenService.Result.failed

        self.sprint("Image generated and sent successfully")
        return ChatImageGenService.Result.success
