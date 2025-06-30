from enum import Enum
from uuid import UUID

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.schema.user import User
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.external_tools.access_token_resolver import AccessTokenResolver
from features.external_tools.external_tool_library import CLAUDE_3_5_HAIKU
from features.images.stable_diffusion_image_generator import StableDiffusionImageGenerator
from features.prompting import prompt_library
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


class GenerativeImagingManager(SafePrinterMixin):
    class Result(Enum):
        success = "Success"
        failed = "Failed"

    __chat_id: str
    __bot_sdk: TelegramBotSDK
    __invoker_user: User
    __llm_input: list[BaseMessage]
    __copywriter: BaseChatModel
    __user_dao: UserCRUD
    __token_resolver: AccessTokenResolver

    def __init__(
        self,
        chat_id: str,
        raw_prompt: str,
        invoker_user_id_hex: str,
        bot_sdk: TelegramBotSDK,
        user_dao: UserCRUD,
        sponsorship_dao: SponsorshipCRUD,
    ):
        super().__init__(config.verbose)
        self.__chat_id = chat_id
        self.__bot_sdk = bot_sdk
        self.__user_dao = user_dao
        self.__llm_input = []
        self.__llm_input.append(SystemMessage(prompt_library.generator_stable_diffusion))
        self.__llm_input.append(HumanMessage(raw_prompt))

        self.__validate(invoker_user_id_hex)
        self.__token_resolver = AccessTokenResolver(
            invoker_user = self.__invoker_user,
            user_dao = user_dao,
            sponsorship_dao = sponsorship_dao,
        )
        anthropic_token = self.__token_resolver.require_access_token_for_tool(CLAUDE_3_5_HAIKU)

        # noinspection PyArgumentList
        self.__copywriter = ChatAnthropic(
            model_name = CLAUDE_3_5_HAIKU.id,
            temperature = 1.0,
            max_tokens = 200,
            timeout = float(config.web_timeout_s),
            max_retries = config.web_retries,
            api_key = anthropic_token,
        )

    def __validate(self, invoker_user_id_hex: str):
        self.sprint("Validating invoker data")
        invoker_user_db = self.__user_dao.get(UUID(hex = invoker_user_id_hex))
        if not invoker_user_db:
            message = f"Invoker '{invoker_user_id_hex}' not found"
            self.sprint(message)
            raise ValueError(message)
        self.__invoker_user = User.model_validate(invoker_user_db)

    def execute(self) -> Result:
        self.sprint(f"Generating image for chat '{self.__chat_id}'")

        # let's correct/prettify and translate the prompt first
        try:
            self.sprint("Starting prompt correction")
            response = self.__copywriter.invoke(self.__llm_input)
            if not isinstance(response, AIMessage) or not isinstance(response.content, str):
                raise AssertionError(f"Received a complex message from LLM: {response}")
            prompt = response.content
            self.sprint(f"Finished prompt correction, new size is {len(prompt)} characters")
        except Exception as e:
            self.sprint("Error correcting raw prompt", e)
            return GenerativeImagingManager.Result.failed

        # let's generate the image now using the corrected prompt
        try:
            self.sprint("Starting image generation")
            replicate_token = self.__token_resolver.require_access_token_for_tool(StableDiffusionImageGenerator.get_tool())
            generator = StableDiffusionImageGenerator(prompt, replicate_token)
            image_url = generator.execute()
            if not image_url:
                self.sprint("Failed to generate image (no image URL found)")
                return GenerativeImagingManager.Result.failed
        except Exception as e:
            self.sprint("Error generating image", e)
            return GenerativeImagingManager.Result.failed

        # let's send the image to the chat
        try:
            self.sprint("Starting image sending")
            self.__bot_sdk.send_photo(self.__chat_id, image_url)
        except Exception as e:
            self.sprint("Error sending image", e)
            return GenerativeImagingManager.Result.failed

        self.sprint("Image generated and sent successfully")
        return GenerativeImagingManager.Result.success
