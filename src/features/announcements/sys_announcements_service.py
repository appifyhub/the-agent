from datetime import datetime, timedelta

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from db.model.chat_config import ChatConfigDB
from db.schema.chat_config import ChatConfig
from db.schema.chat_message import ChatMessage
from db.schema.user import User
from di.di import DI
from features.external_tools.configured_tool import ConfiguredTool
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import CLAUDE_4_6_SONNET
from features.integrations import prompt_resolvers
from features.integrations.integrations import resolve_external_id
from util import log

WHATSAPP_MESSAGING_WINDOW_HOURS = 24


# Not tested as it's just a proxy
class SysAnnouncementsService:

    DEFAULT_TOOL: ExternalTool = CLAUDE_4_6_SONNET
    TOOL_TYPE: ToolType = ToolType.copywriting

    __di: DI
    __llm_input: list[BaseMessage]
    __copywriter: BaseChatModel
    __resolved_chat: ChatConfig

    def __init__(
        self,
        raw_information: str,
        target_chat: ChatConfig | None,
        configured_tool: ConfiguredTool,
        di: DI,
    ):
        self.__di = di
        resolved_chat = target_chat if target_chat else self.__resolve_target_chat()
        if not resolved_chat:
            raise ValueError("Cannot resolve target chat for announcement")

        validated_chat = di.authorization_service.validate_chat(resolved_chat)
        self.__resolved_chat = validated_chat
        system_prompt = prompt_resolvers.copywriting_new_system_event(validated_chat)
        self.__llm_input = []
        self.__llm_input.append(SystemMessage(system_prompt))
        self.__llm_input.append(HumanMessage(raw_information))
        self.__copywriter = di.chat_langchain_model(configured_tool)

    def execute(self) -> tuple[ChatConfig, AIMessage]:
        log.t(f"Starting information announcer for {str(self.__llm_input[-1].content).replace('\n', ' \\n ')}")
        try:
            response = self.__copywriter.invoke(self.__llm_input)
            if not isinstance(response, AIMessage):
                raise AssertionError(f"Received a non-AI message from LLM: {response}")
            log.d(f"Finished announcement creation, summary size is {len(response.content)} characters")
            return self.__resolved_chat, response
        except Exception as e:
            log.e("Information announcement failed", e)
            raise e

    def __resolve_target_chat(self) -> ChatConfig | None:
        """Tries to find the most appropriate chat to message to."""

        telegram_chat = self.__find_private_chat(self.__di.invoker, ChatConfigDB.ChatType.telegram)
        telegram_last_message_at = self.__get_last_user_message_time(telegram_chat, self.__di.invoker) if telegram_chat else None
        is_telegram_eligible = telegram_chat is not None and telegram_last_message_at is not None

        whatsapp_chat = self.__find_private_chat(self.__di.invoker, ChatConfigDB.ChatType.whatsapp)
        whatsapp_last_message_at = self.__get_last_user_message_time(whatsapp_chat, self.__di.invoker) if whatsapp_chat else None
        is_whatsapp_eligible = (
            whatsapp_chat is not None
            and whatsapp_last_message_at is not None
            and (datetime.now() - whatsapp_last_message_at) < timedelta(hours = WHATSAPP_MESSAGING_WINDOW_HOURS)
        )

        # both are eligible: pick most recent
        if is_whatsapp_eligible and is_telegram_eligible:
            assert whatsapp_last_message_at is not None
            assert telegram_last_message_at is not None
            return whatsapp_chat if whatsapp_last_message_at > telegram_last_message_at else telegram_chat
        # only WhatsApp is eligible
        if is_whatsapp_eligible:
            return whatsapp_chat
        # only Telegram is available
        if telegram_chat is not None:  # we can still send here even without chat history
            return telegram_chat
        return None

    def __find_private_chat(self, user: User, chat_type: ChatConfigDB.ChatType) -> ChatConfig | None:
        external_id = resolve_external_id(user, chat_type)
        if not external_id:
            return None

        chat_db = self.__di.chat_config_crud.get_by_external_identifiers(
            external_id = external_id,
            chat_type = chat_type,
        )
        if not chat_db:
            return None
        chat = ChatConfig.model_validate(chat_db)
        return chat if chat.is_private else None

    def __get_last_user_message_time(self, chat: ChatConfig, user: User) -> datetime | None:
        messages_db = self.__di.chat_message_crud.get_latest_chat_messages(chat.chat_id, limit = 30)
        messages = [ChatMessage.model_validate(message_db) for message_db in messages_db]
        for message in messages:
            if message.author_id == user.id:
                return message.sent_at
        return None
