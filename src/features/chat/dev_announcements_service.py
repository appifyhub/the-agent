from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from db.model.chat_config import ChatConfigDB
from db.model.user import UserDB
from db.schema.chat_config import ChatConfig
from db.schema.user import User
from di.di import DI
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import CLAUDE_3_5_SONNET
from features.external_tools.tool_choice_resolver import ConfiguredTool
from features.integrations import prompt_resolvers
from features.integrations.integrations import lookup_user_by_handle, resolve_agent_user, resolve_external_id
from util import log


class DevAnnouncementsService:

    DEFAULT_TOOL: ExternalTool = CLAUDE_3_5_SONNET
    TOOL_TYPE: ToolType = ToolType.copywriting

    __raw_message: str
    __copywriter: BaseChatModel
    __target_chat: ChatConfig | None
    __di: DI

    def __init__(
        self,
        raw_message: str,
        target_handle: str | None,
        configured_tool: ConfiguredTool,
        di: DI,
    ):
        self.__di = di
        self.__target_chat = None
        self.__validate(target_handle)
        self.__raw_message = raw_message
        self.__copywriter = di.chat_langchain_model(configured_tool)

    def __validate(self, target_handle: str | None):
        log.t("Validating invoker permissions")
        if self.__di.invoker.group < UserDB.Group.developer:
            raise ValueError(log.d(f"Invoker '{self.__di.invoker.id.hex}' is not a developer"))

        chat_type: ChatConfigDB.ChatType | None = self.__di.invoker_chat_type
        log.t(f"Validating target user data of {chat_type.value if chat_type else '<no_platform>'}/'@{target_handle}'")
        if target_handle and chat_type:
            target_user_db = lookup_user_by_handle(target_handle, chat_type, self.__di.user_crud)
            if not target_user_db:
                raise ValueError(log.d(f"Target user '{target_handle}' not found"))
            target_user = User.model_validate(target_user_db)

            # check if user has external ID for the current platform
            external_id = resolve_external_id(target_user, chat_type) or ""
            if not external_id:
                raise ValueError(
                    log.d(f"Target user '{target_handle}' has no external ID for {chat_type.value}"),
                )

            target_chat_db = self.__di.chat_config_crud.get_by_external_identifiers(
                external_id = external_id,
                chat_type = chat_type,
            )
            if not target_chat_db:
                raise ValueError(log.d(f"Target chat '{external_id}' not found"))
            self.__target_chat = ChatConfig.model_validate(target_chat_db)

    def execute(self) -> dict:
        log.t(f"Executing announcement from {self.__di.invoker.id.hex}")
        target_chats: list[ChatConfig]
        if self.__target_chat:
            log.t(f"  Target chat: {self.__target_chat.chat_id}")
            target_chats = [self.__target_chat]
        else:
            log.t("  Targeting all chats")
            # we compare external IDs because user objects contain only those
            chat_type = self.__di.require_invoker_chat_type()
            invoker_external_id = resolve_external_id(self.__di.invoker, chat_type) or ""
            agent_user = resolve_agent_user(chat_type)
            bot_external_id = resolve_external_id(agent_user, chat_type) or ""
            target_chats_db = self.__di.chat_config_crud.get_all(limit = 2048)
            target_chats = [
                ChatConfig.model_validate(chat)
                for chat in target_chats_db
                if chat.external_id not in [bot_external_id, invoker_external_id]
            ]

        summaries_created: int = 0
        chats_notified: int = 0

        # translate and notify for each chat
        translations = self.__di.translations_cache
        for chat in target_chats:
            try:
                scoped_di = self.__di.clone(invoker_chat_id = chat.chat_id.hex)
                summary = translations.get(chat.language_name, chat.language_iso_code)
                if not summary:
                    system_prompt = prompt_resolvers.copywriting_system_announcement(chat.chat_type, chat)
                    messages = [SystemMessage(system_prompt), HumanMessage(self.__raw_message)]
                    answer = self.__copywriter.invoke(messages)
                    if not isinstance(answer, AIMessage):
                        raise AssertionError(f"Received a non-AI message from LLM: {answer}")
                    summary = translations.save(str(answer.content), chat.language_name, chat.language_iso_code)
                    summaries_created += 1
                scoped_di.telegram_bot_sdk.send_text_message(int(chat.external_id or "-1"), summary)
                chats_notified += 1
            except Exception as e:
                log.e(f"Announcement failed for chat #{chat.chat_id}", e)

        log.i(f"Chats: {len(target_chats)}, summaries created: {summaries_created}, notified: {chats_notified}")
        return {
            "chats_selected": len(target_chats),
            "chats_notified": chats_notified,
            "summaries_created": summaries_created,
        }
