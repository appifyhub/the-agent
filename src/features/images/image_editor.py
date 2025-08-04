import os
import tempfile
from urllib.parse import urlparse

import requests
from httpx import Timeout
from replicate.client import Client

from features.chat.supported_files import KNOWN_IMAGE_FORMATS
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import IMAGE_EDITING_FLUX_KONTEXT_PRO
from features.external_tools.tool_choice_resolver import ConfiguredTool
from util import log
from util.functions import first_key_with_value

BOOT_AND_RUN_TIMEOUT_S = 120


# Not tested as it's just a proxy
class ImageEditor:

    DEFAULT_TOOL: ExternalTool = IMAGE_EDITING_FLUX_KONTEXT_PRO
    TOOL_TYPE: ToolType = ToolType.images_edit

    error: str | None
    __context: str | None
    __image_url: str
    __configured_tool: ConfiguredTool
    __mime_type: str | None
    __replicate: Client

    def __init__(
        self,
        image_url: str,
        configured_tool: ConfiguredTool,
        context: str | None = None,
        mime_type: str | None = None,
    ):
        self.__context = context
        self.__image_url = image_url
        self.__configured_tool = configured_tool
        self.__mime_type = mime_type
        _, token, _ = configured_tool
        self.__replicate = Client(
            api_token = token.get_secret_value(),
            timeout = Timeout(BOOT_AND_RUN_TIMEOUT_S),
        )

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
                    input_data = {
                        "prompt": self.__context or "",
                        "image": file,
                        "input_image": file,
                        "aspect_ratio": "match_input_image",
                        "output_format": "png",
                        "safety_tolerance": 2,
                        "guidance_scale": 5.5,
                    }
                    tool, _, _ = self.__configured_tool
                    result = self.__replicate.run(tool.id, input = input_data)
            if not result:
                raise ValueError("Failed to edit the image (no output URL)")
            log.d("Image edit successful")
            return str(result)
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
        if self.__mime_type:
            return first_key_with_value(KNOWN_IMAGE_FORMATS, self.__mime_type) or ".none"
        return ""
