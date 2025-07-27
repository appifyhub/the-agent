import base64
import re

import requests
from requests import Response

from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

UPLOAD_URL = "https://freeimghost.net/api/1/upload"
DEFAULT_EXPIRATION_M = 1  # minutes


# Not tested as it's just a proxy
class ImageUploader(SafePrinterMixin):
    __base64_image: str
    __expiration_m: int

    def __init__(
        self,
        binary_image: bytes | None = None,
        base64_image: str | None = None,
        expiration_m: int | None = None,
    ):
        super().__init__(config.verbose)
        if binary_image is None and base64_image is None:
            raise ValueError("Either binary_image or base64_image must be provided")
        if binary_image:
            self.__base64_image = base64.b64encode(binary_image).decode("utf-8")
        if base64_image:
            self.__base64_image = base64_image
        # get rid of data URI prefixes
        self.__base64_image = re.sub(r"^data:image/[^;]+;base64,", "", self.__base64_image)
        self.__expiration_m = expiration_m or DEFAULT_EXPIRATION_M
        image_size_kb = len(base64.b64decode(self.__base64_image)) / 1024
        self.sprint(f"Ready to upload image! Size: {image_size_kb:.2f} KB")

    def execute(self) -> str:
        response: Response | None = None
        try:
            self.sprint("Uploading image now...")
            data = {
                "key": config.free_img_host_token.get_secret_value(),
                "source": self.__base64_image,
                "expiration": f"PT{self.__expiration_m}M",  # ISO 8601 duration format
            }
            response = requests.post(UPLOAD_URL, data = data, timeout = config.web_timeout_s * 2)
            self.sprint(f"Response {response.status_code} received!")
            response.raise_for_status()
            response_data = response.json()
            image_url: str | None = response_data.get("image", {}).get("url", "")
            if not image_url:
                message = "Image upload failed: No image URL returned in response"
                self.sprint(message)
                raise ValueError(message)
            self.sprint("Image uploaded successfully!")
            return image_url
        except Exception as e:
            message = f"Image upload failed: {str(e)}\nResponse: {response.text if response is not None else 'No response'}"
            self.sprint(message, e)
            raise e
