import os
import tempfile
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from httpx import Timeout
from replicate.client import Client

from features.chat.supported_files import KNOWN_IMAGE_FORMATS
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import IMAGE_INPAINTING, IMAGE_RESTORATION
from features.external_tools.tool_choice_resolver import ConfiguredTool
from util import log
from util.functions import first_key_with_value

BOOT_AND_RUN_TIMEOUT_S = 300


# Not tested as it's just a proxy
class ImageContentsRestorer:

    DEFAULT_RESTORATION_TOOL: ExternalTool = IMAGE_RESTORATION
    RESTORATION_TOOL_TYPE: ToolType = ToolType.images_restoration
    DEFAULT_INPAINTING_TOOL: ExternalTool = IMAGE_INPAINTING
    INPAINTING_TOOL_TYPE: ToolType = ToolType.images_inpainting

    @dataclass
    class Result:
        restored_url: str | None
        inpainted_url: str | None
        error: str | None

    __image_url: str
    __restoration_tool: ConfiguredTool
    __inpainting_tool: ConfiguredTool
    __mime_type: str | None
    __prompt_positive: str | None
    __prompt_negative: str | None
    __replicate_restoration: Client
    __replicate_inpainting: Client

    def __init__(
        self,
        image_url: str,
        restoration_tool: ConfiguredTool,
        inpainting_tool: ConfiguredTool,
        prompt_positive: str | None = None,
        prompt_negative: str | None = None,
        mime_type: str | None = None,
    ):
        self.__image_url = image_url
        self.__restoration_tool = restoration_tool
        self.__inpainting_tool = inpainting_tool
        self.__mime_type = mime_type
        self.__prompt_positive = prompt_positive
        self.__prompt_negative = prompt_negative
        _, restoration_token, _ = restoration_tool
        self.__replicate_restoration = Client(
            api_token = restoration_token.get_secret_value(),
            timeout = Timeout(BOOT_AND_RUN_TIMEOUT_S),
        )
        _, inpainting_token, _ = inpainting_tool
        self.__replicate_inpainting = Client(
            api_token = inpainting_token.get_secret_value(),
            timeout = Timeout(BOOT_AND_RUN_TIMEOUT_S),
        )

    def execute(self) -> Result:
        result = ImageContentsRestorer.Result(None, None, None)

        # let's do the basic restoring first
        try:
            log.t("Starting image contents restoration")
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
                    restoration_tool, _, _ = self.__restoration_tool
                    restored_url = self.__replicate_restoration.run(restoration_tool.id, input = input_data)
            if not restored_url:
                raise ValueError("Failed to restore image contents (no output URL)")
            log.d("Image contents restoration successful")
            # noinspection PyTypeChecker
            result.restored_url = str(restored_url)
        except Exception as e:
            result.error = log.w("Error restoring image contents", e)

        # then let's do the more advanced inpainting
        try:
            log.t("Starting image details inpainting")
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
                    inpainting_tool, _, _ = self.__inpainting_tool
                    inpainted_url = list(self.__replicate_inpainting.run(inpainting_tool.id, input = input_data))
            if not inpainted_url or not inpainted_url[0]:
                raise ValueError("Failed to inpaint image details (no output URL)")
            log.d("Image detail inpainting successful")
            result.inpainted_url = inpainted_url[0]
        except Exception as e:
            result.error = log.w("Error inpainting image details", e)
        return result

    def __get_suffix(self, image_url: str) -> str:
        # check if the URL already contains a file extension
        url_path = urlparse(image_url).path
        file_with_extension = os.path.splitext(url_path)[1]
        if file_with_extension:
            return f".{file_with_extension.lstrip('.')}"
        # if no extension in URL, use MIME type to determine extension
        if self.__mime_type:
            return first_key_with_value(KNOWN_IMAGE_FORMATS, self.__mime_type) or ".none"
        return ""
