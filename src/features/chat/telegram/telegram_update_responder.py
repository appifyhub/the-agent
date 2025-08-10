from itertools import chain

from fastapi import HTTPException
from langchain_core.messages import AIMessage, HumanMessage

from db.schema.chat_message import ChatMessage
from db.schema.chat_message_attachment import ChatMessageAttachment
from db.sql import get_detached_session
from di.di import DI
from features.chat.telegram.model.update import Update
from features.chat.telegram.telegram_chat_bot import TelegramChatBot
from features.chat.telegram.telegram_data_resolver import TelegramDataResolver
from features.prompting import prompt_library
from features.prompting.prompt_library import TELEGRAM_BOT_USER
from util import log
from util.config import config
from util.functions import silent


def respond_to_update(update: Update) -> bool:
    if config.log_telegram_update:
        log.t(f"Received a Telegram update: `{update}`")

    with get_detached_session() as db:
        di = DI(db)

        def map_to_langchain(message) -> HumanMessage | AIMessage:
            return di.domain_langchain_mapper.map_to_langchain(di.user_crud.get(message.author_id), message)

        assert TELEGRAM_BOT_USER.id is not None
        if not di.user_crud.get(TELEGRAM_BOT_USER.id):
            di.user_crud.save(TELEGRAM_BOT_USER)

        resolved_domain_data: TelegramDataResolver.Result | None = None
        try:
            # map to storage models for persistence
            domain_update = di.telegram_domain_mapper.map_update(update)
            if not domain_update:
                raise HTTPException(status_code = 422, detail = "Unable to map the update")

            # store and map to domain models (throws in case of error)
            resolved_domain_data = di.telegram_data_resolver.resolve(domain_update)
            if not resolved_domain_data.author:
                log.d("Not responding to messages without author")
                return False
            di.inject_invoker(resolved_domain_data.author)
            di.inject_invoker_chat(resolved_domain_data.chat)

            # fetch latest messages to prepare a response
            past_messages_db = di.chat_message_crud.get_latest_chat_messages(
                chat_id = resolved_domain_data.chat.chat_id,
                limit = config.chat_history_depth,
            )
            past_messages = [ChatMessage.model_validate(chat_message) for chat_message in past_messages_db]
            # now we flat-map to get attachments: chat_message_attachment_dao.get_by_message(chat_id, message_id)
            # but we only have a singular get by 1 message, so we need to fetch all attachments for each message
            past_attachments_db = list(
                chain.from_iterable(
                    di.chat_message_attachment_crud.get_by_message(message.chat_id, message.message_id)
                    for message in past_messages
                ),
            )
            past_attachment_ids = [ChatMessageAttachment.model_validate(attachment).id for attachment in past_attachments_db]
            # DB sorting is date descending
            langchain_messages = [map_to_langchain(message) for message in past_messages][::-1]

            # process the update using LLM; get instead of require to allow the first message to be sent
            tool = di.tool_choice_resolver.get_tool(TelegramChatBot.TOOL_TYPE, TelegramChatBot.DEFAULT_TOOL)
            telegram_chat_bot = di.telegram_chat_bot(
                list(langchain_messages),
                domain_update.message.text,  # excludes the resolver formatting
                domain_update.message.message_id,
                past_attachment_ids,
                tool,
            )
            answer = telegram_chat_bot.execute()
            if not answer or not answer.content:
                log.d("Resolved an empty response, skipping bot reply")
                return False

            # send and store the response[s]
            sent_messages: int = 0
            domain_messages = di.domain_langchain_mapper.map_bot_message_to_storage(resolved_domain_data.chat.chat_id, answer)
            for message in domain_messages:
                di.telegram_bot_sdk.send_text_message(str(resolved_domain_data.chat.external_id), message.text)
                sent_messages += 1

            log.t(f"Finished responding to updates. \n[{TELEGRAM_BOT_USER.full_name}]: {answer.content}")
            log.i(f"Used {len(past_messages_db)} and sent {sent_messages} messages")
            return True
        except Exception as e:
            log.e(f"Failed to ingest: {update}", e)
            __notify_of_errors(di, resolved_domain_data, e)
            return False


@silent
def __notify_of_errors(
    di: DI,
    resolved_domain_data: TelegramDataResolver.Result | None,
    error: Exception,
):
    if resolved_domain_data:
        answer = AIMessage(prompt_library.error_general_problem(str(error)))
        messages = di.domain_langchain_mapper.map_bot_message_to_storage(resolved_domain_data.chat.chat_id, answer)
        for message in messages:
            di.telegram_bot_sdk.send_text_message(str(resolved_domain_data.chat.external_id), message.text)
        log.t("Replied with the error")
