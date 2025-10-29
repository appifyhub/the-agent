from itertools import chain

from langchain_core.messages import AIMessage, HumanMessage

from db.model.chat_config import ChatConfigDB
from db.schema.chat_message import ChatMessage
from db.schema.chat_message_attachment import ChatMessageAttachment
from db.schema.user import User
from db.sql import get_detached_session
from di.di import DI
from features.chat.chat_agent import ChatAgent
from features.chat.whatsapp.model.update import Update
from features.chat.whatsapp.whatsapp_data_resolver import WhatsAppDataResolver
from features.integrations import prompt_resolvers
from features.integrations.integrations import resolve_agent_user
from util import log
from util.config import config
from util.functions import silent


def respond_to_update(update: Update) -> bool:
    if config.log_whatsapp_update:
        log.t(f"Received a WhatsApp update: `{update}`")

    with get_detached_session() as db:
        di = DI(db)

        def map_to_langchain(message) -> HumanMessage | AIMessage:
            author_db = di.user_crud.get(message.author_id)
            author = User.model_validate(author_db) if author_db else None
            return di.domain_langchain_mapper.map_to_langchain(
                author = author,
                message = message,
                chat_type = ChatConfigDB.ChatType.whatsapp,
            )

        resolved_domain_data_all: list[WhatsAppDataResolver.Result] = []
        resolved_domain_data: WhatsAppDataResolver.Result | None = None
        try:
            # map to storage models for persistence
            domain_update = di.whatsapp_domain_mapper.map_update(update)
            if not domain_update:
                log.w("No messages to process in this WhatsApp update (likely a status update or notification)")
                return False

            # store and map to domain models (throws in case of error)
            resolved_domain_data_all = di.whatsapp_data_resolver.resolve_all(domain_update)
            # filter out messages without authors
            resolved_domain_data_all = [message for message in resolved_domain_data_all if message.author]
            if not resolved_domain_data_all:
                log.d("Not responding to messages without authors")
                return False
            # we inject DI context for the latest message only, so let's sort by timestamp
            resolved_domain_data = max(resolved_domain_data_all, key = lambda r: r.message.sent_at)
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
            tool = di.tool_choice_resolver.get_tool(ChatAgent.TOOL_TYPE, ChatAgent.DEFAULT_TOOL)
            chat_agent = di.chat_agent(
                messages = list(langchain_messages),
                raw_last_message = resolved_domain_data.message.text,  # excludes the resolver formatting
                last_message_id = resolved_domain_data.message.message_id,
                attachment_ids = past_attachment_ids,
                configured_tool = tool,
            )
            answer = chat_agent.execute()
            if not answer or not answer.content:
                log.d("No LLM response needed (command handled or no reply required)")
                return False

            # send and store the response[s]
            sent_messages: int = 0
            domain_messages = di.domain_langchain_mapper.map_bot_message_to_storage(resolved_domain_data.chat, answer)
            for message in domain_messages:
                di.whatsapp_bot_sdk.send_text_message(str(resolved_domain_data.chat.external_id), message.text)
                sent_messages += 1

            # mark the incoming message as read
            di.whatsapp_bot_sdk.mark_as_read(resolved_domain_data.message.message_id)

            agent = resolve_agent_user(resolved_domain_data.chat.chat_type)
            log.t(f"Finished responding to updates. \n[{agent.full_name}]: {answer.content}")
            log.i(f"Used {len(past_messages_db)} and sent {sent_messages} messages")
            return True
        except Exception as e:
            log.e(f"Failed to ingest: {update}", e)
            __notify_of_errors(di, resolved_domain_data, e)
            return False


@silent
def __notify_of_errors(
    di: DI,
    resolved_domain_data: WhatsAppDataResolver.Result | None,
    error: Exception,
):
    if resolved_domain_data:
        answer = AIMessage(prompt_resolvers.simple_chat_error(str(error)))
        messages = di.domain_langchain_mapper.map_bot_message_to_storage(resolved_domain_data.chat, answer)
        for message in messages:
            di.whatsapp_bot_sdk.send_text_message(str(resolved_domain_data.chat.external_id), message.text)
        log.t("Replied with the error")
