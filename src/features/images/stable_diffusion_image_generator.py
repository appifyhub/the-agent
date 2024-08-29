import replicate
from httpx import Timeout
from replicate import Client

from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

BASIC_MODEL = "black-forest-labs/flux-schnell"
ADVANCED_MODEL = "black-forest-labs/flux-dev"
IMAGE_ASPECT_RATIO = "3:2"
OUTPUT_FORMAT = "png"
OUTPUT_QUALITY = 100
INFERENCE_STEPS = 25


class StableDiffusionImageGenerator(SafePrinterMixin):
    __prompt: str
    __use_advanced_model: bool
    __replicate: Client

    def __init__(
        self,
        prompt: str,
        use_advanced_model: bool,
        replicate_api_key: str,
    ):
        super().__init__(config.verbose)
        self.__prompt = prompt
        self.__use_advanced_model = use_advanced_model
        self.__replicate = replicate.Client(
            api_token = replicate_api_key,
            timeout = Timeout(config.web_timeout_s * 2),
        )

    def execute(self) -> str | None:
        self.sprint(f"Starting stable diffusion generator with prompt: '{self.__prompt}'")
        model = ADVANCED_MODEL if self.__use_advanced_model else BASIC_MODEL
        self.sprint(f"Using model: '{model}'")
        try:
            result = self.__replicate.run(
                model,
                input = {
                    "prompt": self.__prompt,
                    "aspect_ratio": IMAGE_ASPECT_RATIO,
                    "output_format": OUTPUT_FORMAT,
                    "output_quality": OUTPUT_QUALITY,
                    "num_inference_steps": INFERENCE_STEPS,
                    "num_outputs": 1,
                }
            )
            return result[0]  # return the first URL
        except Exception as e:
            self.sprint(f"Failed to generate image", e)
            return None
