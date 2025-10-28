import base64
import re

import requests
from requests import Response

from util import log
from util.config import config

UPLOAD_URL = "https://api.imgbb.com/1/upload"
DEFAULT_EXPIRATION_M = 1  # minutes


# Not tested as it's just a proxy
class ImageUploader:

    __base64_image: str
    __expiration_s: int
    __name: str | None

    def __init__(
        self,
        binary_image: bytes | None = None,
        base64_image: str | None = None,
        expiration_s: int | None = None,
        name: str | None = None,
    ):
        if binary_image is None and base64_image is None:
            raise ValueError("Either binary_image or base64_image must be provided")
        if binary_image:
            self.__base64_image = base64.b64encode(binary_image).decode("utf-8")
        if base64_image:
            self.__base64_image = base64_image
        # get rid of data URI prefixes
        self.__base64_image = re.sub(r"^data:image/[^;]+;base64,", "", self.__base64_image)
        self.__expiration_s = expiration_s or (DEFAULT_EXPIRATION_M * 60)
        self.__name = name
        image_size_kb = len(base64.b64decode(self.__base64_image)) / 1024
        log.t(f"Ready to upload image! Size: {image_size_kb:.2f} KB")

    def execute(self) -> str:
        response: Response | None = None
        try:
            log.t("Uploading image now...")
            data = {
                "key": config.free_img_host_token.get_secret_value(),
                "image": self.__base64_image,
                "expiration": self.__expiration_s,
            }
            if self.__name:
                data["name"] = self.__name
            response = requests.post(UPLOAD_URL, data = data, timeout = config.web_timeout_s * 2)
            log.t(f"Response HTTP-{response.status_code} received!")
            response.raise_for_status()
            response_data = response.json()

            # Check if the response indicates success
            if not response_data.get("success", False):
                error_msg = response_data.get("error", {}).get("message", "Unknown error")
                raise ValueError(f"Image upload failed: {error_msg}")

            # Try to get the image URL from the response
            # The API documentation doesn't specify the exact structure, so we'll try common patterns
            image_url: str | None = (
                response_data.get("data", {}).get("url") or
                response_data.get("image", {}).get("url") or
                response_data.get("url")
            )

            if not image_url:
                raise ValueError("Image upload failed: No image URL returned in response")
            log.t("Image uploaded successfully!")
            return image_url
        except Exception as e:
            message = log.w("Image upload failed!", {response.text if response is not None else "No response"}, e)
            raise ValueError(message)
