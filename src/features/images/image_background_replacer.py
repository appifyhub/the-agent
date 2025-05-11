import base64
import concurrent.futures
import os
import tempfile
from urllib.parse import urlparse

import replicate
import requests
from httpx import Timeout
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from pydantic import SecretStr
from replicate import Client

from features.ai_tools.external_ai_tool_library import CLAUDE_3_5_SONNET, BACKGROUND_REPLACEMENT
from features.chat.supported_files import KNOWN_IMAGE_FORMATS
from features.images.computer_vision_analyzer import ComputerVisionAnalyzer
from features.images.image_contents_restorer import ImageContentsRestorer
from features.prompting import prompt_library
from util.config import config
from util.functions import first_key_with_value
from util.safe_printer_mixin import SafePrinterMixin

DEFAULT_IMAGE_EXTENSION = "png"
DEFAULT_IMAGE_MIME_TYPE = "image/png"
IMAGE_DESCRIPTION_TASK = "Describe the image in as much detail as possible, including the style/art and quality"
BOOT_AND_RUN_TIMEOUT_S = 420


# Not tested as it's just a proxy
class ImageBackgroundReplacer(SafePrinterMixin):
    __job_id: str
    __image_url: str
    __image_contents: bytes
    __image_contents_b64: str
    __image_extension: str
    __mime_type: str
    __change_request: str
    __how_many_variants: int
    __replicate: Client
    __copywriter: BaseChatModel
    __vision: ComputerVisionAnalyzer

    def __init__(
        self,
        job_id: str,
        image_url: str,
        change_request: str,
        replicate_api_key: str,
        anthropic_api_key: str,
        open_ai_api_key: str,
        how_many_variants: int = 1,
        mime_type: str | None = None,
    ):
        super().__init__(config.verbose)
        self.__job_id = job_id
        self.__image_url = image_url
        self.__image_contents = requests.get(self.__image_url).content
        self.__image_contents_b64 = base64.b64encode(self.__image_contents).decode("utf-8")
        self.__mime_type = mime_type  # start with a default to be able to use it in __get_suffix()
        self.__image_extension = self.__get_suffix().replace(".", "") or DEFAULT_IMAGE_EXTENSION
        self.__mime_type = mime_type or KNOWN_IMAGE_FORMATS.get(self.__image_extension) or DEFAULT_IMAGE_MIME_TYPE
        self.__change_request = change_request
        self.__how_many_variants = how_many_variants
        self.__replicate = replicate.Client(
            api_token = replicate_api_key,
            timeout = Timeout(BOOT_AND_RUN_TIMEOUT_S),
        )
        # noinspection PyArgumentList
        self.__copywriter = ChatAnthropic(
            model_name = CLAUDE_3_5_SONNET.id,
            temperature = 1.0,
            max_tokens = 200,
            timeout = float(config.web_timeout_s),
            max_retries = config.web_retries,
            api_key = SecretStr(str(anthropic_api_key)),
        )
        self.__vision = ComputerVisionAnalyzer(
            job_id = self.__job_id,
            image_mime_type = mime_type,
            open_ai_api_key = open_ai_api_key,
            image_b64 = self.__image_contents_b64,
            additional_context = IMAGE_DESCRIPTION_TASK,
        )

    def generate_image_description(self) -> str | None:
        self.sprint(f"Generating an image description for job '{self.__job_id}'")
        return self.__vision.execute()

    def create_guided_prompt(self, image_description: str, positive: bool) -> str | None:
        self.sprint(f"Guiding a prompt for job '{self.__job_id}', positive: {positive}")
        try:
            system_message = prompt_library.generator_guided_diffusion_positive if positive \
                else prompt_library.generator_guided_diffusion_negative
            task_message = f"[IMAGE DESCRIPTION]\n{image_description}\n\n[CHANGE REQUEST]\n{self.__change_request}"
            response = self.__copywriter.invoke([SystemMessage(system_message), HumanMessage(task_message)])
            if not isinstance(response, AIMessage) or not isinstance(response.content, str):
                raise AssertionError(f"Received a complex message from LLM: {response}")
            prompt = response.content
            self.sprint(f"Finished prompt guidance, new size is {len(prompt)} characters")
            return prompt
        except Exception as e:
            self.sprint("Error guiding prompt", e)
            return None

    def replace_background(self, prompt_positive: str, prompt_negative: str) -> list[str]:
        self.sprint("Starting background replacement")
        try:
            # not using the URL directly because it contains the bot token in its path
            with tempfile.NamedTemporaryFile(delete = True, suffix = f".{self.__image_extension}") as temp_file:
                temp_file.write(self.__image_contents)
                temp_file.flush()
                with open(temp_file.name, "rb") as file:
                    input_data = {
                        "image": file,
                        "steps": 40,
                        "prompt": prompt_positive,
                        "negative_prompt": prompt_negative,
                        "batch_count": self.__how_many_variants,
                    }
                    result = self.__replicate.run(
                        BACKGROUND_REPLACEMENT.id,
                        input = input_data,
                    )
            if not result or not result.get("images"):
                self.sprint("Failed to replace background (no output URLs)")
                return []
            self.sprint("Background replacement successful")
            return result["images"][:-1]  # last one is the mask
        except Exception as e:
            self.sprint("Error replacing background", e)
            return []

    def restore_image_contents(
        self,
        prompt_positive: str,
        prompt_negative: str,
        image_urls: list[str],
    ) -> tuple[list[str], list[str]]:
        """
        Restores image contents and returns a list of new image URLs. One contains all restored URLs and the other
        contains all URLs with inpainted details.
        """
        self.sprint("Starting image restoration (in parallel)")

        def restore(image_url: str) -> ImageContentsRestorer.Result:
            # noinspection PyProtectedMember
            return ImageContentsRestorer(
                image_url = image_url,
                replicate_api_key = self.__replicate._api_token,
                prompt_positive = prompt_positive,
                prompt_negative = prompt_negative,
                mime_type = self.__mime_type,
            ).execute()

        with concurrent.futures.ThreadPoolExecutor(max_workers = len(image_urls)) as scheduler:
            results = list(scheduler.map(restore, image_urls))

        restored_urls = [result.restored_url for result in results if result.restored_url is not None]
        inpainted_urls = [result.inpainted_url for result in results if result.inpainted_url is not None]
        return restored_urls, inpainted_urls

    def execute(self) -> list[str]:
        self.sprint("Starting background replacement")
        try:
            description = self.generate_image_description()
            if not description:
                raise ValueError("Image analysis failed, no description")
            prompt_positive = self.create_guided_prompt(description, positive = True)
            if not prompt_positive:
                raise ValueError("Positive prompt guidance failed, no prompt")
            prompt_negative = self.create_guided_prompt(description, positive = False)
            if not prompt_negative:
                raise ValueError("Negative prompt guidance failed, no prompt")
            replaced_background_urls = self.replace_background(prompt_positive, prompt_negative)
            if not replaced_background_urls:
                raise ValueError("Background replacement failed, no URLs")
            restored_urls, inpainted_urls = self.restore_image_contents(
                prompt_positive, prompt_negative, replaced_background_urls,
            )
            all_urls = replaced_background_urls + restored_urls + inpainted_urls
            final_results = [url for url in all_urls if url is not None]
            return final_results
        except Exception as e:
            self.sprint("Failed to replace background", e)
            raise e  # propagate to the caller

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
