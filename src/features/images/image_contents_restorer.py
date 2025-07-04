import os
import tempfile
from urllib.parse import urlparse

import requests
from httpx import Timeout
from pydantic import SecretStr
from replicate.client import Client

from features.chat.supported_files import KNOWN_IMAGE_FORMATS
from features.external_tools.external_tool import ExternalTool
from features.external_tools.external_tool_library import IMAGE_INPAINTING, IMAGE_RESTORATION
from util.config import config
from util.functions import first_key_with_value
from util.safe_printer_mixin import SafePrinterMixin

BOOT_AND_RUN_TIMEOUT_S = 300


# Not tested as it's just a proxy
class ImageContentsRestorer(SafePrinterMixin):
    class Result:
        restored_url: str | None
        inpainted_url: str | None

        def __init__(self, restored_url: str | None, inpainted_url: str | None):
            self.restored_url = restored_url
            self.inpainted_url = inpainted_url

    __image_url: str
    __mime_type: str | None
    __prompt_positive: str | None
    __prompt_negative: str | None
    __replicate: Client

    def __init__(
        self,
        image_url: str,
        replicate_api_key: SecretStr,
        prompt_positive: str | None = None,
        prompt_negative: str | None = None,
        mime_type: str | None = None,
    ):
        super().__init__(config.verbose)
        self.__image_url = image_url
        self.__mime_type = mime_type
        self.__prompt_positive = prompt_positive
        self.__prompt_negative = prompt_negative
        self.__replicate = Client(
            api_token = replicate_api_key.get_secret_value(),
            timeout = Timeout(BOOT_AND_RUN_TIMEOUT_S),
        )

    @staticmethod
    def get_resoration_tool() -> ExternalTool:
        return IMAGE_RESTORATION

    @staticmethod
    def get_inpainting_tool() -> ExternalTool:
        return IMAGE_INPAINTING

    def execute(self) -> Result:
        result = ImageContentsRestorer.Result(None, None)

        # let's do the basic restoring first
        try:
            self.sprint("Starting image contents restoration")
            # not using the URL directly because it contains the bot token in its path
            with tempfile.NamedTemporaryFile(delete = True, suffix = self.__get_suffix(self.__image_url)) as temp_file:
                response = requests.get(self.__image_url)
                temp_file.write(response.content)
                temp_file.flush()
                with open(temp_file.name, "rb") as file:
                    input_data = {
                        "image": file,
                        "upscale": 2,
                        "face_upsample": True,
                        "background_enhance": True,
                        "codeformer_fidelity": 0.1,
                    }
                    restored_url = self.__replicate.run(
                        ImageContentsRestorer.get_resoration_tool().id,
                        input = input_data,
                    )
            if not restored_url:
                raise ValueError("Failed to restore image contents (no output URL)")
            self.sprint("Image contents restoration successful")
            # noinspection PyTypeChecker
            result.restored_url = str(restored_url)
        except Exception as e:
            self.sprint("Error restoring image contents", e)

        # then let's do the more advanced inpainting
        try:
            self.sprint("Starting image details inpainting")
            url_to_inpaint = result.restored_url or self.__image_url
            # same thing about the URL privacy
            with tempfile.NamedTemporaryFile(delete = True, suffix = self.__get_suffix(url_to_inpaint)) as temp_file:
                response = requests.get(url_to_inpaint)
                temp_file.write(response.content)
                temp_file.flush()
                with open(temp_file.name, "rb") as file:
                    input_data = {
                        "image": file,
                        "hdr": 0.2,
                        "steps": 100,
                        "prompt": self.__prompt_positive or "High quality image",
                        "creativity": 0.05,
                        "resemblance": 0.95,
                        "guidance_scale": 0.1,
                        "negative_prompt": self.__prompt_negative or "bad anatomy, ugly, low quality",
                    }
                    inpainted_url = self.__replicate.run(
                        ImageContentsRestorer.get_inpainting_tool().id,
                        input = input_data,
                    )
            if not inpainted_url or not inpainted_url[0]:
                raise ValueError("Failed to inpaint image details (no output URL)")
            self.sprint("Image detail inpainting successful")
            result.inpainted_url = inpainted_url[0]
        except Exception as e:
            self.sprint("Error inpainting image details", e)
        return result

    def __get_suffix(self, image_url: str) -> str:
        # check if the URL already contains a file extension
        url_path = urlparse(image_url).path
        file_with_extension = os.path.splitext(url_path)[1]
        if file_with_extension:
            return f".{file_with_extension.lstrip('.')}"
        # if no extension in URL, use MIME type to determine extension
        if self.__mime_type:
            return first_key_with_value(KNOWN_IMAGE_FORMATS, self.__mime_type)
        return ""
