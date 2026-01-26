from dataclasses import asdict

from google.genai.types import GenerateContentConfig, ImageConfig

from di.di import DI
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import IMAGE_GEN_FLUX_1_1
from features.external_tools.external_tool_provider_library import GOOGLE_AI, REPLICATE
from features.external_tools.tool_choice_resolver import ConfiguredTool
from features.images.image_api_utils import map_to_model_parameters
from util import log
from util.config import config
from util.functions import extract_url_from_replicate_result


# Not tested as it's just a proxy
class SimpleStableDiffusionGenerator:

    DEFAULT_TOOL: ExternalTool = IMAGE_GEN_FLUX_1_1
    TOOL_TYPE: ToolType = ToolType.images_gen

    error: str | None
    __prompt: str
    __configured_tool: ConfiguredTool
    __aspect_ratio: str | None
    __output_size: str | None
    __di: DI

    def __init__(
        self,
        prompt: str,
        configured_tool: ConfiguredTool,
        di: DI,
        aspect_ratio: str | None = None,
        output_size: str | None = None,
    ):
        self.__di = di
        self.__prompt = prompt
        self.__configured_tool = configured_tool
        self.__aspect_ratio = aspect_ratio
        self.__output_size = output_size

    def execute(self) -> str | None:
        log.t(f"Starting text-stable-diffusion generator with prompt: '{self.__prompt}'")
        self.error = None
        try:
            if self.__configured_tool.definition.provider == REPLICATE:
                return self.__generate_with_replicate()
            elif self.__configured_tool.definition.provider == GOOGLE_AI:
                return self.__generate_with_google_ai()
            else:
                raise ValueError(f"Unsupported provider: '{self.__configured_tool.definition.provider}'")
        except Exception as e:
            self.error = log.e("Failed to generate image", e)
            return None

    def __generate_with_replicate(self) -> str | None:
        log.t("Generating image with Replicate")

        unified_params = map_to_model_parameters(
            tool = self.__configured_tool.definition, prompt = self.__prompt,
            aspect_ratio = self.__aspect_ratio, output_size = self.__output_size,
        )
        dict_params = {
            k: v for k, v in unified_params.__dict__.items() if v is not None
        }
        log.t("Calling Replicate image generator with params", dict_params)

        replicate = self.__di.replicate_client(
            self.__configured_tool,
            config.web_timeout_s * 10,
            output_image_sizes = [unified_params.size] if unified_params.size else None,
            input_image_sizes = None,
        )
        prediction = replicate.predictions.create(
            version = self.__configured_tool.definition.id,
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

        unified_params = map_to_model_parameters(
            tool = self.__configured_tool.definition, prompt = self.__prompt,
            aspect_ratio = self.__aspect_ratio, output_size = self.__output_size,
        )
        dict_params = asdict(unified_params)
        log.t("Calling Google AI image generator API with params", dict_params)

        google_ai = self.__di.google_ai_client(
            self.__configured_tool,
            config.web_timeout_s * 10,
            output_image_sizes = [unified_params.size] if unified_params.size else None,
            input_image_sizes = None,
        )
        image_config = ImageConfig(aspect_ratio = unified_params.aspect_ratio, image_size = unified_params.size)
        response = google_ai.models.generate_content(
            model = self.__configured_tool.definition.id,
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
