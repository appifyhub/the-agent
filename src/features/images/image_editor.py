import os
import tempfile
from urllib.parse import urlparse

import requests

from di.di import DI
from features.chat.supported_files import KNOWN_IMAGE_FORMATS
from features.external_tools.configured_tool import ConfiguredTool
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import IMAGE_GEN_EDIT_FLUX_KONTEXT_PRO
from features.images.image_api_utils import map_to_model_parameters
from features.images.image_size_utils import calculate_image_size_category
from util import log
from util.error_codes import IMAGE_EDIT_FAILED
from util.errors import ExternalServiceError
from util.functions import extract_url_from_replicate_result, first_key_with_value

BOOT_AND_RUN_TIMEOUT_S = 120


# Not tested as it's just a proxy
class ImageEditor:

    DEFAULT_TOOL: ExternalTool = IMAGE_GEN_EDIT_FLUX_KONTEXT_PRO
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

                with open(temp_file.name, "rb") as file:
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
        except Exception as e:
            self.error = f"Error editing image: {str(e)}"
            log.e("Error editing image", e)
            return None

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
