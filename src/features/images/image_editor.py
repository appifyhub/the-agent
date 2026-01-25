import os
import tempfile
from urllib.parse import urlparse

import requests
from replicate.client import Client

from di.di import DI
from features.chat.supported_files import KNOWN_IMAGE_FORMATS
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import IMAGE_EDITING_FLUX_KONTEXT_PRO
from features.external_tools.tool_choice_resolver import ConfiguredTool
from features.images.image_api_utils import map_to_model_parameters
from util import log
from util.functions import extract_url_from_replicate_result, first_key_with_value

BOOT_AND_RUN_TIMEOUT_S = 120


# Not tested as it's just a proxy
class ImageEditor:

    DEFAULT_TOOL: ExternalTool = IMAGE_EDITING_FLUX_KONTEXT_PRO
    TOOL_TYPE: ToolType = ToolType.images_edit

    error: str | None
    __prompt: str
    __image_url: str
    __configured_tool: ConfiguredTool
    __input_mime_type: str | None
    __aspect_ratio: str | None
    __size: str | None
    __replicate: Client
    __di: DI

    def __init__(
        self,
        image_url: str,
        configured_tool: ConfiguredTool,
        prompt: str,
        di: DI,
        input_mime_type: str | None = None,
        aspect_ratio: str | None = None,
        size: str | None = None,
    ):
        self.__prompt = prompt
        self.__image_url = image_url
        self.__configured_tool = configured_tool
        self.__input_mime_type = input_mime_type
        self.__aspect_ratio = aspect_ratio
        self.__size = size
        self.__di = di
        self.__replicate = self.__di.replicate_client(configured_tool, BOOT_AND_RUN_TIMEOUT_S, self.__size)

    def execute(self) -> str | None:
        log.d("Starting photo editing")
        self.error = None
        try:
            # not using the URL directly because it contains the bot token in its path
            with tempfile.NamedTemporaryFile(delete = True, suffix = self.__get_suffix()) as temp_file:
                response = requests.get(self.__image_url)
                temp_file.write(response.content)
                temp_file.flush()
                with open(temp_file.name, "rb") as file:
                    tool, _, _ = self.__configured_tool
                    unified_params = map_to_model_parameters(
                        tool = tool, prompt = self.__prompt,
                        aspect_ratio = self.__aspect_ratio, size = self.__size,
                        input_files = [file],
                    )
                    dict_params = {
                        k: v for k, v in unified_params.__dict__.items() if v is not None
                    }
                    log.t("Calling Replicate image editing with params", dict_params)

                    prediction = self.__replicate.predictions.create(
                        version = tool.id,
                        input = dict_params,
                    )
                    prediction.wait()

                    result = prediction.output
            if not result:
                raise ValueError("Failed to edit the image (no result returned)")
            log.d("Image edit successful")
            return extract_url_from_replicate_result(result)
        except Exception as e:
            self.error = log.e("Error editing image", e)
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
