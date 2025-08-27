from enum import Enum

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from di.di import DI
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import CLAUDE_3_5_HAIKU
from features.external_tools.tool_choice_resolver import ConfiguredTool
from features.images.simple_stable_diffusion_generator import SimpleStableDiffusionGenerator
from features.integrations import prompt_resolvers
from util import log


class SmartStableDiffusionGenerator:

    class Result(Enum):
        success = "Success"
        failed = "Failed"

    DEFAULT_COPYWRITER_TOOL: ExternalTool = CLAUDE_3_5_HAIKU
    COPYWRITER_TOOL_TYPE: ToolType = ToolType.copywriting

    DEFAULT_IMAGE_GEN_TOOL: ExternalTool = SimpleStableDiffusionGenerator.DEFAULT_TOOL
    IMAGE_GEN_TOOL_TYPE: ToolType = SimpleStableDiffusionGenerator.TOOL_TYPE

    error: str | None = None
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
        system_prompt = prompt_resolvers.copywriting_image_prompt_upscaler(di.invoker_chat.chat_type)
        self.__llm_input = [SystemMessage(system_prompt), HumanMessage(raw_prompt)]
        self.__copywriter = di.chat_langchain_model(configured_copywriter_tool)
        self.__image_gen_tool = configured_image_gen_tool
        self.__di = di

    def execute(self) -> Result:
        log.d(f"Generating image for chat '{self.__di.invoker_chat.chat_id}'")
        self.error = None

        # let's correct/prettify and translate the prompt first
        try:
            log.t("Starting prompt upscaling")
            response = self.__copywriter.invoke(self.__llm_input)
            if not isinstance(response, AIMessage) or not isinstance(response.content, str):
                raise AssertionError(f"Received a complex message from LLM: {response}")
            prompt = response.content
            log.t(f"Finished prompt correction, new size is {len(prompt)} characters")
        except Exception as e:
            self.error = log.e("Error correcting raw prompt", e)
            return SmartStableDiffusionGenerator.Result.failed

        # let's generate the image now using the corrected prompt
        try:
            log.t("Starting image generation")
            generator = self.__di.simple_stable_diffusion_generator(prompt, self.__image_gen_tool)
            image_url = generator.execute()
            if generator.error:
                self.error = log.e("Image generator failure", generator.error)
                return SmartStableDiffusionGenerator.Result.failed
            if not image_url:
                self.error = log.e("Image generator failure (no image URL found)")
                return SmartStableDiffusionGenerator.Result.failed
        except Exception as e:
            self.error = log.e("Error generating image", e)
            return SmartStableDiffusionGenerator.Result.failed

        # let's send the image to the chat
        try:
            log.t("Starting image sending")
            self.__di.telegram_bot_sdk.send_document(
                int(self.__di.invoker_chat.external_id or "-1"), image_url, thumbnail = image_url,
            )
            self.__di.telegram_bot_sdk.send_photo(
                int(self.__di.invoker_chat.external_id or "-1"), image_url, caption = "📸",
            )
        except Exception as e:
            self.error = log.e("Error sending image", e)
            return SmartStableDiffusionGenerator.Result.failed

        log.i("Image generated and sent successfully")
        return SmartStableDiffusionGenerator.Result.success
