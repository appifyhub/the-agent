from dataclasses import asdict

from google.genai.client import Client as GoogleClient
from google.genai.types import GenerateContentConfig, ImageConfig
from replicate.client import Client as ReplicateClient

from di.di import DI
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import IMAGE_GENERATION_FLUX_1_1
from features.external_tools.external_tool_provider_library import GOOGLE_AI, REPLICATE
from features.external_tools.tool_choice_resolver import ConfiguredTool
from features.images.image_api_utils import map_to_model_parameters
from util import log
from util.config import config
from util.functions import extract_url_from_replicate_result


# Not tested as it's just a proxy
class SimpleStableDiffusionGenerator:

    DEFAULT_TOOL: ExternalTool = IMAGE_GENERATION_FLUX_1_1
    TOOL_TYPE: ToolType = ToolType.images_gen

    error: str | None
    __prompt: str
    __external_tool: ExternalTool
    __replicate: ReplicateClient | None
    __google_ai: GoogleClient | None
    __aspect_ratio: str | None
    __size: str | None
    __di: DI

    def __init__(
        self,
        prompt: str,
        configured_tool: ConfiguredTool,
        di: DI,
        aspect_ratio: str | None = None,
        size: str | None = None,
    ):
        self.__di = di
        self.__prompt = prompt
        self.__external_tool, _, _ = configured_tool
        self.__aspect_ratio = aspect_ratio
        self.__size = size

        self.__replicate = None
        self.__google_ai = None
        if self.__external_tool.provider == REPLICATE:
            self.__replicate = self.__di.replicate_client(configured_tool, config.web_timeout_s * 10, self.__size)
        elif self.__external_tool.provider == GOOGLE_AI:
            self.__google_ai = self.__di.google_ai_client(configured_tool, config.web_timeout_s * 10, self.__size)
        else:
            raise ValueError(f"Unsupported provider: '{self.__external_tool.provider}'")

    def execute(self) -> str | None:
        log.t(f"Starting text-stable-diffusion generator with prompt: '{self.__prompt}'")
        self.error = None
        try:
            if self.__replicate:
                return self.__generate_with_replicate()
            elif self.__google_ai:
                return self.__generate_with_google_ai()
            else:
                raise ValueError(f"Unsupported provider: '{self.__external_tool.provider}'")
        except Exception as e:
            self.error = log.e("Failed to generate image", e)
            return None

    def __generate_with_replicate(self) -> str | None:
        log.t("Generating image with Replicate")

        unified_params = map_to_model_parameters(
            tool = self.__external_tool, prompt = self.__prompt,
            aspect_ratio = self.__aspect_ratio, size = self.__size,
        )
        dict_params = {
            k: v for k, v in unified_params.__dict__.items() if v is not None
        }
        log.t("Calling Replicate image generator with params", dict_params)

        prediction = self.__replicate.predictions.create(
            version = self.__external_tool.id,
            input = dict_params,
        )
        prediction.wait()

        result = prediction.output
        log.d("Result", result)
        if not result:
            raise ValueError("No result returned from image generation")
        return extract_url_from_replicate_result(result)

    def __generate_with_google_ai(self) -> str | None:
        log.t("Generating image with Google AI")
        if not self.__google_ai:
            raise ValueError("Google AI client is not initialized")

        unified_params = map_to_model_parameters(
            tool = self.__external_tool, prompt = self.__prompt,
            aspect_ratio = self.__aspect_ratio, size = self.__size,
        )
        dict_params = asdict(unified_params)
        log.t("Calling Google AI image generator API with params", dict_params)

        image_config = ImageConfig(
            aspect_ratio = unified_params.aspect_ratio,
            image_size = unified_params.size,
        )

        response = self.__google_ai.models.generate_content(
            model = self.__external_tool.id,
            contents = self.__prompt,
            config = GenerateContentConfig(
                response_modalities = ["TEXT", "IMAGE"],
                image_config = image_config,
            ),
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
