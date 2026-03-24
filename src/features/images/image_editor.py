import base64
import os
import tempfile
from urllib.parse import urlparse

import requests
from google.genai.types import GenerateContentConfig, ImageConfig
from PIL import Image

from di.di import DI
from features.chat.supported_files import KNOWN_IMAGE_FORMATS
from features.external_tools.configured_tool import ConfiguredTool
from features.external_tools.external_tool import ToolType
from features.external_tools.external_tool_provider_library import GOOGLE_AI, REPLICATE, XAI
from features.images.image_api_utils import map_to_model_parameters
from features.images.image_size_utils import calculate_image_size_category
from util import log
from util.config import config
from util.error_codes import EXTERNAL_EMPTY_RESPONSE, IMAGE_EDIT_FAILED, UNSUPPORTED_PROVIDER
from util.errors import ConfigurationError, ExternalServiceError
from util.functions import extract_url_from_replicate_result, first_key_with_value

BOOT_AND_RUN_TIMEOUT_S = 120


# Not tested as it's just a proxy
class ImageEditor:

    TOOL_TYPE: ToolType = ToolType.images_edit

    error: str | None
    __prompt: str
    __image_url: str
    __configured_tool: ConfiguredTool
    __input_mime_type: str | None
    __aspect_ratio: str | None
    __output_size: str | None
    __di: DI

    def __init__(
        self,
        image_url: str,
        configured_tool: ConfiguredTool,
        prompt: str,
        di: DI,
        input_mime_type: str | None = None,
        aspect_ratio: str | None = None,
        output_size: str | None = None,
    ):
        self.__prompt = prompt
        self.__image_url = image_url
        self.__configured_tool = configured_tool
        self.__input_mime_type = input_mime_type
        self.__aspect_ratio = aspect_ratio
        self.__output_size = output_size
        self.__di = di

    def execute(self) -> str | None:
        log.d("Starting photo editing")
        self.error = None
        try:
            # not using the URL directly because it contains the bot token in its path
            with tempfile.NamedTemporaryFile(delete = True, suffix = self.__get_suffix()) as temp_file:
                response = requests.get(self.__image_url)
                temp_file.write(response.content)
                temp_file.flush()

                # Calculate input image size
                input_image_size: str | None = None
                try:
                    input_image_size = calculate_image_size_category(temp_file.name)
                except Exception as e:
                    log.e(f"Failed to calculate input image size, will proceed without it: {e}")

                if self.__configured_tool.definition.provider == REPLICATE:
                    return self.__edit_with_replicate(temp_file.name, input_image_size)
                elif self.__configured_tool.definition.provider == GOOGLE_AI:
                    return self.__edit_with_google_ai(temp_file.name, input_image_size)
                elif self.__configured_tool.definition.provider == XAI:
                    return self.__edit_with_x_ai(temp_file.name, input_image_size)
                else:
                    raise ConfigurationError(f"Unsupported provider: '{self.__configured_tool.definition.provider}'", UNSUPPORTED_PROVIDER)  # noqa: E501
        except Exception as e:
            self.error = f"Error editing image: {str(e)}"
            log.e("Error editing image", e)
            return None

    def __edit_with_replicate(self, temp_file_path: str, input_image_size: str | None) -> str | None:
        log.t("Editing image with Replicate")

        with open(temp_file_path, "rb") as file:
            unified_params = map_to_model_parameters(
                tool = self.__configured_tool.definition, prompt = self.__prompt,
                aspect_ratio = self.__aspect_ratio, output_size = self.__output_size,
                input_files = [file],
            )
            dict_params = {
                k: v for k, v in unified_params.__dict__.items() if v is not None
            }
            log.t("Calling Replicate image editing with params", dict_params)

            replicate = self.__di.replicate_client(
                configured_tool = self.__configured_tool,
                timeout_s = BOOT_AND_RUN_TIMEOUT_S,
                output_image_sizes = [unified_params.size] if unified_params.size else None,
                input_image_sizes = [input_image_size] if input_image_size else None,
            )
            prediction = replicate.predictions.create(version = self.__configured_tool.definition.id, input = dict_params)
            prediction.wait()

            result = prediction.output
        if not result:
            raise ExternalServiceError("Failed to edit the image (no result returned)", IMAGE_EDIT_FAILED)
        log.d("Image edit successful")
        return extract_url_from_replicate_result(result)

    def __edit_with_google_ai(self, temp_file_path: str, input_image_size: str | None) -> str | None:
        log.t("Editing image with Google AI")

        with open(temp_file_path, "rb") as file:
            unified_params = map_to_model_parameters(
                tool = self.__configured_tool.definition, prompt = self.__prompt,
                aspect_ratio = self.__aspect_ratio, output_size = self.__output_size,
                input_files = [file],
            )
        log.t("Calling Google AI image editing API with params", unified_params)

        google_ai = self.__di.google_ai_client(
            self.__configured_tool,
            config.web_timeout_s * 10,
            output_image_sizes = [unified_params.size] if unified_params.size else None,
            input_image_sizes = [input_image_size] if input_image_size else None,
        )
        pil_image = Image.open(temp_file_path)
        image_config = ImageConfig(aspect_ratio = unified_params.aspect_ratio, image_size = unified_params.size)
        response = google_ai.models.generate_content(
            model = self.__configured_tool.definition.id,
            contents = [self.__prompt, pil_image],
            config = GenerateContentConfig(
                response_modalities = ["TEXT", "IMAGE"],
                image_config = image_config,
            ),
        )

        # analyze the response
        if not response or not response.candidates:
            raise ExternalServiceError("No candidates in the response from Google AI", EXTERNAL_EMPTY_RESPONSE)
        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            raise ExternalServiceError("No contents in the top candidate from Google AI", EXTERNAL_EMPTY_RESPONSE)

        # locate the image data in the response
        image_data: bytes | None = None
        for part in candidate.content.parts:
            if part.inline_data is not None:
                image_data = part.inline_data.data
                break
        if image_data is None:
            raise ExternalServiceError("No image data found in Google AI response", EXTERNAL_EMPTY_RESPONSE)

        # upload the image to an external service to get a direct URL
        uploader = self.__di.image_uploader(binary_image = image_data)
        return uploader.execute()

    def __edit_with_x_ai(self, temp_file_path: str, input_image_size: str | None) -> str | None:
        log.t("Editing image with xAI")

        with open(temp_file_path, "rb") as file:
            unified_params = map_to_model_parameters(
                tool = self.__configured_tool.definition, prompt = self.__prompt,
                aspect_ratio = self.__aspect_ratio, output_size = self.__output_size,
                input_files = [file],
            )
        log.t("Calling xAI image editing with params", unified_params)

        with open(temp_file_path, "rb") as file:
            image_bytes = file.read()
        mime_type = self.__input_mime_type or "image/png"
        image_data = base64.b64encode(image_bytes).decode("utf-8")
        image_url = f"data:{mime_type};base64,{image_data}"

        x_ai_client = self.__di.x_ai_client(
            self.__configured_tool,
            config.web_timeout_s * 10,
            output_image_sizes = [unified_params.resolution] if unified_params.resolution else None,
            input_image_sizes = [input_image_size] if input_image_size else None,
        )

        response = x_ai_client.image.sample(
            prompt = self.__prompt,
            model = self.__configured_tool.definition.id,
            image_url = image_url,
            aspect_ratio = unified_params.aspect_ratio,
            resolution = unified_params.resolution,
        )

        log.d("xAI image edit response received")
        if not response:
            raise ExternalServiceError("No response returned from xAI", EXTERNAL_EMPTY_RESPONSE)
        if not response.respect_moderation:
            raise ExternalServiceError("xAI image was filtered by moderation", EXTERNAL_EMPTY_RESPONSE)
        if not response.url:
            raise ExternalServiceError("No image URL returned from xAI", EXTERNAL_EMPTY_RESPONSE)
        return response.url

    def __get_suffix(self) -> str:
        # check if the URL already contains a file extension
        url_path = urlparse(self.__image_url).path
        file_with_extension = os.path.splitext(url_path)[1]
        if file_with_extension:
            return f".{file_with_extension.lstrip('.')}"
        # if no extension in URL, use MIME type to determine extension
        if self.__input_mime_type:
            return first_key_with_value(KNOWN_IMAGE_FORMATS, self.__input_mime_type) or ".none"
        return ""
