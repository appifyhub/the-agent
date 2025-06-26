from httpx import Timeout
from pydantic import SecretStr
from replicate.client import Client

from features.external_tools.external_tool import ExternalTool
from features.external_tools.external_tool_library import IMAGE_GENERATION_FLUX
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


# Not tested as it's just a proxy
class StableDiffusionImageGenerator(SafePrinterMixin):
    __prompt: str
    __replicate: Client

    def __init__(
        self,
        prompt: str,
        replicate_api_key: SecretStr,
    ):
        super().__init__(config.verbose)
        self.__prompt = prompt
        self.__replicate = Client(
            api_token = replicate_api_key.get_secret_value(),
            timeout = Timeout(config.web_timeout_s * 3),  # this takes long
        )

    @staticmethod
    def get_tool() -> ExternalTool:
        return IMAGE_GENERATION_FLUX

    def execute(self) -> str | None:
        self.sprint(f"Starting stable diffusion generator with prompt: '{self.__prompt}'")
        try:
            result = self.__replicate.run(
                StableDiffusionImageGenerator.get_tool().id,
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
