import os
import tempfile
from urllib.parse import urlparse

import requests
from httpx import Timeout
from replicate.client import Client

from features.chat.supported_files import KNOWN_IMAGE_FORMATS
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import BACKGROUND_REMOVAL
from features.external_tools.tool_choice_resolver import ConfiguredTool
from util.config import config
from util.functions import first_key_with_value
from util.safe_printer_mixin import SafePrinterMixin

BOOT_AND_RUN_TIMEOUT_S = 120


# Not tested as it's just a proxy
class ImageBackgroundRemover(SafePrinterMixin):
    DEFAULT_TOOL: ExternalTool = BACKGROUND_REMOVAL
    TOOL_TYPE: ToolType = ToolType.images_background_removal

    error: str | None
    __image_url: str
    __configured_tool: ConfiguredTool
    __mime_type: str | None
    __replicate: Client

    def __init__(
        self,
        image_url: str,
        configured_tool: ConfiguredTool,
        mime_type: str | None = None,
    ):
        super().__init__(config.verbose)
        self.__image_url = image_url
        self.__configured_tool = configured_tool
        self.__mime_type = mime_type
        _, token, _ = configured_tool
        self.__replicate = Client(
            api_token = token.get_secret_value(),
            timeout = Timeout(BOOT_AND_RUN_TIMEOUT_S),
        )

    def execute(self) -> str | None:
        self.sprint("Starting background removal")
        self.error = None
        try:
            # not using the URL directly because it contains the bot token in its path
            with tempfile.NamedTemporaryFile(delete = True, suffix = self.__get_suffix()) as temp_file:
                response = requests.get(self.__image_url)
                temp_file.write(response.content)
                temp_file.flush()
                with open(temp_file.name, "rb") as file:
                    input_data = {"image": file}
                    tool, _, _ = self.__configured_tool
                    result = self.__replicate.run(tool.id, input = input_data)
            if not result:
                raise ValueError("Failed to remove background (no output URL)")
            self.sprint("Background removal successful")
            return str(result)
        except Exception as e:
            self.sprint("Error removing background", e)
            self.error = str(e)
            return None

    def __get_suffix(self) -> str:
        # check if the URL already contains a file extension
        url_path = urlparse(self.__image_url).path
        file_with_extension = os.path.splitext(url_path)[1]
        if file_with_extension:
            return f".{file_with_extension.lstrip(".")}"
        # if no extension in URL, use MIME type to determine extension
        if self.__mime_type:
            return first_key_with_value(KNOWN_IMAGE_FORMATS, self.__mime_type)
        return ""
