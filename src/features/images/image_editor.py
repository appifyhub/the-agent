import os
import tempfile
from urllib.parse import urlparse

import requests
from httpx import Timeout
from pydantic import SecretStr
from replicate.client import Client

from features.chat.supported_files import KNOWN_IMAGE_FORMATS
from features.external_tools.external_tool import ExternalTool
from features.external_tools.external_tool_library import IMAGE_EDITING_FLUX_KONTEXT_PRO
from util.config import config
from util.functions import first_key_with_value
from util.safe_printer_mixin import SafePrinterMixin

BOOT_AND_RUN_TIMEOUT_S = 120


# Not tested as it's just a proxy
class ImageEditor(SafePrinterMixin):
    __context: str | None
    __image_url: str
    __mime_type: str | None
    __replicate: Client

    def __init__(
        self,
        image_url: str,
        replicate_api_key: SecretStr,
        context: str | None = None,
        mime_type: str | None = None,
    ):
        super().__init__(config.verbose)
        self.__context = context
        self.__image_url = image_url
        self.__mime_type = mime_type
        self.__replicate = Client(
            api_token = replicate_api_key.get_secret_value(),
            timeout = Timeout(BOOT_AND_RUN_TIMEOUT_S),
        )

    @staticmethod
    def get_tool() -> ExternalTool:
        return IMAGE_EDITING_FLUX_KONTEXT_PRO

    def execute(self) -> str | None:
        self.sprint("Starting photo editing")
        try:
            # not using the URL directly because it contains the bot token in its path
            with tempfile.NamedTemporaryFile(delete = True, suffix = self.__get_suffix()) as temp_file:
                response = requests.get(self.__image_url)
                temp_file.write(response.content)
                temp_file.flush()
                with open(temp_file.name, "rb") as file:
                    input_data = {
                        "prompt": self.__context or "",
                        "input_image": file,
                        "aspect_ratio": "match_input_image",
                        "output_format": "png",
                        "safety_tolerance": 2,
                    }
                    result = self.__replicate.run(ImageEditor.get_tool().id, input = input_data)
            if not result:
                self.sprint("Failed to edit the image (no output URL)")
                return None
            self.sprint("Image edit successful")
            return str(result)
        except Exception as e:
            self.sprint("Error editing image", e)
            return None

    def __get_suffix(self) -> str:
        # check if the URL already contains a file extension
        url_path = urlparse(self.__image_url).path
        file_with_extension = os.path.splitext(url_path)[1]
        if file_with_extension:
            return f".{file_with_extension.lstrip('.')}"
        # if no extension in URL, use MIME type to determine extension
        if self.__mime_type:
            return first_key_with_value(KNOWN_IMAGE_FORMATS, self.__mime_type)
        return ""
