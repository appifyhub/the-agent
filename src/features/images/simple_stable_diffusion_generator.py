from google import genai
from google.genai.client import Client as GoogleClient
from google.genai.types import GenerateContentConfig, HttpOptions
from httpx import Timeout
from replicate.client import Client as ReplicateClient

from di.di import DI
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import IMAGE_GENERATION_FLUX
from features.external_tools.external_tool_provider_library import GOOGLE_AI, REPLICATE
from features.external_tools.tool_choice_resolver import ConfiguredTool
from util import log
from util.config import config
from util.functions import extract_url_from_replicate_result


# Not tested as it's just a proxy
class SimpleStableDiffusionGenerator:

    DEFAULT_TOOL: ExternalTool = IMAGE_GENERATION_FLUX
    TOOL_TYPE: ToolType = ToolType.images_gen

    error: str | None
    __prompt: str
    __configured_tool: ConfiguredTool
    __replicate: ReplicateClient | None
    __google_ai: GoogleClient | None
    __di: DI

    def __init__(
        self,
        prompt: str,
        configured_tool: ConfiguredTool,
        di: DI,
    ):
        self.__di = di
        self.__prompt = prompt
        self.__configured_tool = configured_tool
        tool, token, _ = self.__configured_tool

        self.__replicate = None
        self.__google_ai = None
        if tool.provider == GOOGLE_AI:
            self.__google_ai = genai.Client(
                api_key = token.get_secret_value(),
                http_options = HttpOptions(
                    timeout = config.web_timeout_s * 5 * 1000,  # this takes quite long, and Google requires milliseconds
                ),
            )
        elif tool.provider == REPLICATE:
            self.__replicate = ReplicateClient(
                api_token = token.get_secret_value(),
                timeout = Timeout(config.web_timeout_s * 5),  # this takes quite long
            )
        else:
            raise ValueError(f"Unsupported provider: '{tool.provider}'")

    def execute(self) -> str | None:
        log.t(f"Starting text-stable-diffusion generator with prompt: '{self.__prompt}'")
        tool, _, _ = self.__configured_tool
        self.error = None
        try:
            if tool.provider == REPLICATE:
                return self.__generate_with_replicate()
            elif tool.provider == GOOGLE_AI:
                return self.__generate_with_google_ai()
            else:
                raise ValueError(f"Unsupported provider: '{tool.provider}'")
        except Exception as e:
            self.error = log.e("Failed to generate image", e)
            return None

    def __generate_with_replicate(self) -> str | None:
        log.t("Generating image with Replicate")
        tool, _, _ = self.__configured_tool
        if not self.__replicate:
            raise ValueError("Replicate client is not initialized")
        result = self.__replicate.run(
            tool.id,
            input = {
                "prompt": self.__prompt,
                "prompt_upsampling": True,
                "aspect_ratio": "2:3",
                "output_format": "png",
                "output_quality": 100,
                "num_inference_steps": 30,
                "safety_tolerance": 0,
                "guidance_scale": 5.5,
                "num_outputs": 1,
                "size": "4K",
                "max_images": 1,
                "sequential_image_generation": "disabled",
            },
        )
        log.d("Result", result)
        if not result:
            raise ValueError("No result returned from image generation")
        return extract_url_from_replicate_result(result)

    def __generate_with_google_ai(self) -> str | None:
        log.t("Generating image with Google AI")
        tool, _, _ = self.__configured_tool
        if not self.__google_ai:
            raise ValueError("Google AI client is not initialized")

        # generate the image
        response = self.__google_ai.models.generate_content(
            model = tool.id,
            contents = self.__prompt,
            config = GenerateContentConfig(response_modalities = ["TEXT", "IMAGE"]),
        )

        # analyze the response
        if not response or not response.candidates:
            raise ValueError("No candidates in the response from Google AI")
        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            raise ValueError("No contents in the top candidate from Google AI")

        # locate the image data in the response
        image_data: bytes | None = None
        for part in candidate.content.parts:
            if part.inline_data is not None:
                image_data = part.inline_data.data
                break
        if image_data is None:
            raise ValueError("No image data found in Google AI response")

        # upload the image to an external service to get a direct URL
        uploader = self.__di.image_uploader(binary_image = image_data)
        return uploader.execute()
