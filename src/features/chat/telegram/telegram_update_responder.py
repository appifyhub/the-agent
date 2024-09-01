from fastapi import HTTPException
from langchain_core.messages import AIMessage

from db.crud.chat_message import ChatMessageCRUD
from db.crud.user import UserCRUD
from db.schema.chat_message import ChatMessage
from features.chat.telegram.domain_langchain_mapper import DomainLangchainMapper
from features.chat.telegram.model.update import Update
from features.chat.telegram.telegram_bot_api import TelegramBotAPI
from features.chat.telegram.telegram_chat_bot import TelegramChatBot
from features.chat.telegram.telegram_data_resolver import TelegramDataResolver
from features.chat.telegram.telegram_domain_mapper import TelegramDomainMapper
from features.chat.command_processor import CommandProcessor
from features.chat.invite_manager import InviteManager
from features.prompting import prompt_library
from features.prompting.prompt_library import TELEGRAM_BOT_USER
from util.config import config
from util.functions import silent
from util.safe_printer_mixin import sprint


def respond_to_update(
    user_dao: UserCRUD,
    invite_manager: InviteManager,
    chat_messages_dao: ChatMessageCRUD,
    telegram_domain_mapper: TelegramDomainMapper,
    telegram_data_resolver: TelegramDataResolver,
    domain_langchain_mapper: DomainLangchainMapper,
    telegram_bot_api: TelegramBotAPI,
    update: Update,
) -> bool:
    user_dao.save(TELEGRAM_BOT_USER)  # save is ignored if bot already exists
    resolved_domain_data: TelegramDataResolver.Result | None = None
    try:
        # map to storage models for persistence
        domain_update = telegram_domain_mapper.map_update(update)
        if not domain_update: raise HTTPException(status_code = 422, detail = "Unable to map the update")

        # store and map to domain models (throws in case of error)
        resolved_domain_data = telegram_data_resolver.resolve(domain_update)
        sprint(f"Imported updates from Telegram: {resolved_domain_data}")

        # fetch latest messages to prepare a response
        past_messages_db = chat_messages_dao.get_latest_chat_messages(
            chat_id = resolved_domain_data.chat.chat_id,
            limit = config.chat_history_depth,
        )
        past_messages = [ChatMessage.model_validate(chat_message) for chat_message in past_messages_db]
        map_to_lc = lambda message: domain_langchain_mapper.map_to_langchain(user_dao.get(message.author_id), message)
        langchain_messages = [map_to_lc(message) for message in past_messages][::-1]  # DB sorting is date descending

        # process the update using LLM
        if not resolved_domain_data.author:
            sprint("Not responding to messages without author")
            return False
        command_processor = CommandProcessor(resolved_domain_data.author, user_dao, invite_manager)
        telegram_chat_bot = TelegramChatBot(
            resolved_domain_data.chat,
            resolved_domain_data.author,
            langchain_messages,
            domain_update.message.text,
            command_processor,
        )
        answer = telegram_chat_bot.execute()
        if not answer.content:
            sprint("Resolved an empty response, skipping bot reply")
            return False

        # send and store the response[s]
        sent_messages: int = 0
        saved_messages: int = 0
        domain_messages = domain_langchain_mapper.map_bot_message_to_storage(
            resolved_domain_data.chat.chat_id,
            answer,
        )
        for message in domain_messages:
            telegram_bot_api.send_text_message(message.chat_id, message.text)
            sent_messages += 1
            chat_messages_dao.save(message)
            saved_messages += 1
        sprint(f"Finished responding to updates. \n[{TELEGRAM_BOT_USER.full_name}]: {answer.content}")
        sprint(f"Used {len(past_messages_db)}, saved {saved_messages}, sent {sent_messages} messages")
        return True
    except Exception as e:
        sprint(f"Failed to ingest: {update}", e)
        __notify_of_errors(chat_messages_dao, domain_langchain_mapper, telegram_bot_api, resolved_domain_data, e)
        return False


@silent
def __notify_of_errors(
    chat_messages_dao: ChatMessageCRUD,
    domain_langchain_mapper: DomainLangchainMapper,
    telegram_bot_api: TelegramBotAPI,
    resolved_domain_data: TelegramDataResolver.Result | None,
    error: Exception,
):
    if resolved_domain_data:
        answer = AIMessage(prompt_library.error_general_problem(str(error)))
        messages = domain_langchain_mapper.map_bot_message_to_storage(resolved_domain_data.chat.chat_id, answer)
        for message in messages:
            telegram_bot_api.send_text_message(message.chat_id, message.text)
            chat_messages_dao.save(message)
        sprint("Replied with the error")
