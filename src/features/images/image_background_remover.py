import os
import tempfile
from urllib.parse import urlparse

import replicate
import requests
from httpx import Timeout
from replicate import Client

from features.images.computer_vision_analyzer import KNOWN_IMAGE_FORMATS
from util.config import config
from util.functions import first_key_with_value
from util.safe_printer_mixin import SafePrinterMixin

BACKGROUND_REMOVER_MODEL = "cjwbw/rembg:fb8af171cfa1616ddcf1242c093f9c46bcada5ad4cf6f2fbe8b81b330ec5c003"
BOOT_AND_RUN_TIMEOUT_S = 100


# Not tested as it's just a proxy
class ImageBackgroundRemover(SafePrinterMixin):
    __image_url: str
    __mime_type: str | None
    __replicate: Client

    def __init__(
        self,
        image_url: str,
        replicate_api_key: str,
        mime_type: str | None = None,
    ):
        super().__init__(config.verbose)
        self.__image_url = image_url
        self.__mime_type = mime_type
        self.__replicate = replicate.Client(
            api_token = replicate_api_key,
            timeout = Timeout(BOOT_AND_RUN_TIMEOUT_S),
        )

    def execute(self) -> str | None:
        self.sprint("Starting background removal")
        try:
            with tempfile.NamedTemporaryFile(delete = True, suffix = self.__get_suffix()) as temp_file:
                response = requests.get(self.__image_url)
                temp_file.write(response.content)
                temp_file.flush()
                with open(temp_file.name, "rb") as file:
                    input_data = {"image": file}
                    result = self.__replicate.run(BACKGROUND_REMOVER_MODEL, input = input_data)
            if not result:
                self.sprint("Failed to remove background (no output URL)")
                return None
            self.sprint("Background removal successful")
            return str(result)
        except Exception as e:
            self.sprint("Error removing background", e)
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
