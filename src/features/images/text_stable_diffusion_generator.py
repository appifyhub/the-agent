from httpx import Timeout
from replicate.client import Client

from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import IMAGE_GENERATION_FLUX
from features.external_tools.tool_choice_resolver import ConfiguredTool
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


# Not tested as it's just a proxy
class TextStableDiffusionGenerator(SafePrinterMixin):
    DEFAULT_TOOL: ExternalTool = IMAGE_GENERATION_FLUX
    TOOL_TYPE: ToolType = ToolType.images_gen

    __prompt: str
    __configured_tool: ConfiguredTool
    __replicate: Client

    def __init__(
        self,
        prompt: str,
        configured_tool: ConfiguredTool,
    ):
        super().__init__(config.verbose)
        self.__prompt = prompt
        self.__configured_tool = configured_tool
        _, token, _ = self.__configured_tool
        self.__replicate = Client(
            api_token = token.get_secret_value(),
            timeout = Timeout(config.web_timeout_s * 5),  # this takes quite long
        )

    def execute(self) -> str | None:
        self.sprint(f"Starting text-stable-diffusion generator with prompt: '{self.__prompt}'")
        tool, _, _ = self.__configured_tool
        try:
            result = self.__replicate.run(
                tool.id,
                input = {
                    "prompt": self.__prompt,
                    "prompt_upsampling": True,
                    "aspect_ratio": "2:3",
                    "output_format": "png",
                    "output_quality": 100,
                    "num_inference_steps": 30,
                    "safety_tolerance": 5,
                    "num_outputs": 1,
                },
            )
            if isinstance(result, list):
                if result and isinstance(result[0], str):
                    return result[0]
                return None
            elif isinstance(result, str):
                return result
            elif result is not None:
                return str(result)
            return None
        except Exception as e:
            self.sprint("Failed to generate image", e)
            return None
