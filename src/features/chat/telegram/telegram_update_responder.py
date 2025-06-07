from fastapi import HTTPException
from langchain_core.messages import AIMessage

from db.crud.chat_config import ChatConfigCRUD
from db.crud.chat_message import ChatMessageCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.schema.chat_message import ChatMessage
from db.sql import get_detached_session
from features.chat.command_processor import CommandProcessor
from api.settings_controller import SettingsController
from features.chat.sponsorship_manager import SponsorshipManager
from features.chat.telegram.domain_langchain_mapper import DomainLangchainMapper
from features.chat.telegram.model.update import Update
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.chat.telegram.telegram_chat_bot import TelegramChatBot
from features.chat.telegram.telegram_data_resolver import TelegramDataResolver
from features.chat.telegram.telegram_domain_mapper import TelegramDomainMapper
from features.chat.telegram.telegram_progress_notifier import TelegramProgressNotifier
from features.prompting import prompt_library
from features.prompting.prompt_library import TELEGRAM_BOT_USER
from util.config import config
from util.functions import silent
from util.safe_printer_mixin import sprint


def respond_to_update(update: Update) -> bool:
    if config.log_telegram_update:
        sprint(f"Received a Telegram update: `{update}`")

    with get_detached_session() as db:
        user_dao = UserCRUD(db)
        sponsorship_dao = SponsorshipCRUD(db)
        sponsorship_manager = SponsorshipManager(user_dao, sponsorship_dao)
        chat_message_dao = ChatMessageCRUD(db)
        chat_config_dao = ChatConfigCRUD(db)
        telegram_bot_sdk = TelegramBotSDK(db)
        telegram_domain_mapper = TelegramDomainMapper()
        domain_langchain_mapper = DomainLangchainMapper()
        telegram_data_resolver = TelegramDataResolver(db, telegram_bot_sdk.api)

        def map_to_langchain(message):
            return domain_langchain_mapper.map_to_langchain(user_dao.get(message.author_id), message)

        user_dao.save(TELEGRAM_BOT_USER)  # save is ignored if bot already exists
        resolved_domain_data: TelegramDataResolver.Result | None = None
        try:
            # map to storage models for persistence
            domain_update = telegram_domain_mapper.map_update(update)
            if not domain_update:
                raise HTTPException(status_code = 422, detail = "Unable to map the update")

            # store and map to domain models (throws in case of error)
            resolved_domain_data = telegram_data_resolver.resolve(domain_update)
            # sprint(f"Imported updates from Telegram: {resolved_domain_data}")

            # fetch latest messages to prepare a response
            past_messages_db = chat_message_dao.get_latest_chat_messages(
                chat_id = resolved_domain_data.chat.chat_id,
                limit = config.chat_history_depth,
            )
            past_messages = [ChatMessage.model_validate(chat_message) for chat_message in past_messages_db]
            # DB sorting is date descending
            langchain_messages = [map_to_langchain(message) for message in past_messages][::-1]

            # process the update using LLM
            if not resolved_domain_data.author:
                sprint("Not responding to messages without author")
                return False

            settings_controller = SettingsController(
                invoker_user_id_hex = resolved_domain_data.author.id.hex,
                telegram_sdk = telegram_bot_sdk,
                user_dao = user_dao,
                chat_config_dao = chat_config_dao,
            )
            command_processor = CommandProcessor(
                invoker = resolved_domain_data.author,
                user_dao = user_dao,
                sponsorship_manager = sponsorship_manager,
                settings_controller = settings_controller,
                telegram_sdk = telegram_bot_sdk,
            )
            progress_notifier = TelegramProgressNotifier(
                resolved_domain_data.chat,
                domain_update.message.message_id,
                telegram_bot_sdk,
                auto_start = False,
            )
            telegram_chat_bot = TelegramChatBot(
                resolved_domain_data.chat,
                resolved_domain_data.author,
                langchain_messages,
                domain_update.message.text,  # excluding the resolver formatting
                command_processor,
                progress_notifier,
            )
            answer = telegram_chat_bot.execute()
            if not answer.content:
                sprint("Resolved an empty response, skipping bot reply")
                return False

            # send and store the response[s]
            sent_messages: int = 0
            domain_messages = domain_langchain_mapper.map_bot_message_to_storage(
                resolved_domain_data.chat.chat_id,
                answer,
            )
            for message in domain_messages:
                telegram_bot_sdk.send_text_message(message.chat_id, message.text)
                sent_messages += 1
            sprint(f"Finished responding to updates. \n[{TELEGRAM_BOT_USER.full_name}]: {answer.content}")
            sprint(f"Used {len(past_messages_db)}, sent {sent_messages} messages")
            return True
        except Exception as e:
            sprint(f"Failed to ingest: {update}", e)
            __notify_of_errors(domain_langchain_mapper, telegram_bot_sdk, resolved_domain_data, e)
            return False


@silent
def __notify_of_errors(
    domain_langchain_mapper: DomainLangchainMapper,
    telegram_bot_sdk: TelegramBotSDK,
    resolved_domain_data: TelegramDataResolver.Result | None,
    error: Exception,
):
    if resolved_domain_data:
        answer = AIMessage(prompt_library.error_general_problem(str(error)))
        messages = domain_langchain_mapper.map_bot_message_to_storage(resolved_domain_data.chat.chat_id, answer)
        for message in messages:
            telegram_bot_sdk.send_text_message(message.chat_id, message.text)
        sprint("Replied with the error")
