from datetime import datetime
from enum import Enum
from uuid import UUID

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage

from db.crud.user import UserCRUD
from db.model.user import UserDB
from db.schema.user import User
from features.chat.telegram.model.message import Message
from features.chat.telegram.model.update import Update
from features.chat.telegram.telegram_bot_api import TelegramBotAPI
from features.chat.telegram.telegram_data_resolver import TelegramDataResolver
from features.chat.telegram.telegram_domain_mapper import TelegramDomainMapper
from features.images.stable_diffusion_image_generator import StableDiffusionImageGenerator
from features.prompting import prompt_library
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

ANTHROPIC_AI_MODEL = "claude-3-5-sonnet-20240620"
ANTHROPIC_AI_TEMPERATURE = 0.8
ANTHROPIC_MAX_TOKENS = 200


class GenerativeImagingManager(SafePrinterMixin):
    class Result(Enum):
        success = "Success"
        failed = "Failed"

    __chat_id: str
    __use_advanced_model: bool
    __bot_api: TelegramBotAPI
    __invoker_user: User
    __llm_input: list[BaseMessage]
    __llm: BaseChatModel
    __user_dao: UserCRUD

    def __init__(
        self,
        chat_id: str,
        raw_prompt: str,
        invoker_user_id_hex: str,
        bot_api: TelegramBotAPI,
        user_dao: UserCRUD,
    ):
        super().__init__(config.verbose)
        self.__chat_id = chat_id
        self.__bot_api = bot_api
        self.__user_dao = user_dao
        self.__llm_input = []
        self.__llm_input.append(SystemMessage(prompt_library.generator_stable_diffusion))
        self.__llm_input.append(HumanMessage(raw_prompt))
        # noinspection PyArgumentList
        self.__llm = ChatAnthropic(
            model_name = ANTHROPIC_AI_MODEL,
            temperature = ANTHROPIC_AI_TEMPERATURE,
            max_tokens = ANTHROPIC_MAX_TOKENS,
            timeout = float(config.web_timeout_s),
            max_retries = config.web_retries,
            api_key = str(config.anthropic_token),
        )
        self.validate(invoker_user_id_hex)

    def validate(self, invoker_user_id_hex: str):
        self.sprint("Validating invoker data")
        invoker_user_db = self.__user_dao.get(UUID(hex = invoker_user_id_hex))
        if not invoker_user_db:
            message = f"Invoker '{invoker_user_id_hex}' not found"
            self.sprint(message)
            raise ValueError(message)
        self.__invoker_user = User.model_validate(invoker_user_db)

        self.__use_advanced_model = self.__invoker_user.group >= UserDB.Group.alpha
        if self.__invoker_user.group < UserDB.Group.beta:
            message = f"Invoker '{invoker_user_id_hex}' is not allowed to generate images"
            self.sprint(message)
            raise ValueError(message)

    def execute(self) -> Result:
        self.sprint(f"Generating image for chat '{self.__chat_id}'")

        # let's correct/prettify and translate the prompt first
        try:
            self.sprint("Starting prompt correction")
            response = self.__llm.invoke(self.__llm_input)
            if not isinstance(response, AIMessage) or not isinstance(response.content, str):
                raise AssertionError(f"Received a complex message from LLM: {response}")
            prompt = response.content
            self.sprint(f"Finished prompt correction, new size is {len(prompt)} characters")
        except Exception as e:
            self.sprint(f"Error correcting raw prompt", e)
            return GenerativeImagingManager.Result.failed

        # let's generate the image now using the corrected prompt
        try:
            self.sprint("Starting image generation")
            generator = StableDiffusionImageGenerator(
                prompt = prompt,
                use_advanced_model = self.__use_advanced_model,
                replicate_api_key = config.replicate_api_token,
            )
            image_url = generator.execute()
            if not image_url:
                self.sprint("Failed to generate image (no image found)")
                return GenerativeImagingManager.Result.failed
        except Exception as e:
            self.sprint(f"Error generating image", e)
            return GenerativeImagingManager.Result.failed

        # let's send the image to the chat
        try:
            self.sprint("Starting image sending")
            result_json = self.__bot_api.send_photo(self.__chat_id, image_url)
            if not result_json:
                raise ValueError("No response from Telegram API")
            self.store_bot_photo(result_json)
        except Exception as e:
            self.sprint(f"Error sending image", e)
            return GenerativeImagingManager.Result.failed

        self.sprint("Image generated and sent successfully")
        return GenerativeImagingManager.Result.success

    def store_bot_photo(self, api_result: dict):
        self.sprint(f"Storing message data")
        message = Message(**api_result["result"])
        update = Update(update_id = datetime.now().second, message = message)
        mapping_result = TelegramDomainMapper().map_update(update)
        if not mapping_result:
            raise ValueError("No mapping result from Telegram API")
        # noinspection PyProtectedMember
        resolver = TelegramDataResolver(self.__user_dao._db, self.__bot_api)
        resolution_result = resolver.resolve(mapping_result)
        if not resolution_result.message or not resolution_result.attachments:
            raise ValueError("No resolution result from storing new data")
