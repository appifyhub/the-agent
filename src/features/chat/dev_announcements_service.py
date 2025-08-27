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
from features.integrations.integrations import resolve_agent_user
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
        target_telegram_username: str | None,
        configured_tool: ConfiguredTool,
        di: DI,
    ):
        self.__raw_message = raw_message
        self.__di = di
        self.__validate(target_telegram_username)
        self.__copywriter = di.chat_langchain_model(configured_tool)

    def __validate(self, target_telegram_username: str | None):
        log.t("Validating invoker permissions")
        if self.__di.invoker.group < UserDB.Group.developer:
            raise ValueError(log.d(f"Invoker '{self.__di.invoker.id.hex}' is not a developer"))

        log.t("Validating target user data")
        self.__target_chat = None
        if target_telegram_username:
            target_user_db = self.__di.user_crud.get_by_telegram_username(target_telegram_username)
            if not target_user_db:
                raise ValueError(log.d(f"Target user '{target_telegram_username}' not found"))
            target_user = User.model_validate(target_user_db)
            if not target_user.telegram_chat_id:
                raise ValueError(log.d(f"Target user '{target_telegram_username}' has no private chat ID yet"))
            # TODO don't hard-code Telegram
            target_chat_db = self.__di.chat_config_crud.get_by_external_identifiers(
                external_id = str(target_user.telegram_chat_id),
                chat_type = ChatConfigDB.ChatType.telegram,
            )
            if not target_chat_db:
                raise ValueError(log.d(f"Target chat '{target_user.telegram_chat_id}' not found"))
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
            invoker_external_chat_id = str(self.__di.invoker.telegram_chat_id)
            # TODO don't hard-code Telegram
            agent_user = resolve_agent_user(ChatConfigDB.ChatType.telegram)
            bot_external_chat_id = str(agent_user.telegram_chat_id)
            target_chats_db = self.__di.chat_config_crud.get_all(limit = 2048)
            target_chats = [
                ChatConfig.model_validate(chat)
                for chat in target_chats_db
                if chat.external_id not in [bot_external_chat_id, invoker_external_chat_id]
            ]

        summaries_created: int = 0
        chats_notified: int = 0

        # translate for default language
        translations = self.__di.translations_cache
        try:
            answer = self.__create_announcement(target_chat = None)
            translations.save(str(answer.content))
            summaries_created += 1
        except Exception as e:
            log.e("Announcement translation failed for default language", e)

        # translate and notify for each chat
        for chat in target_chats:
            try:
                summary = translations.get(chat.language_name, chat.language_iso_code)
                if not summary:
                    answer = self.__create_announcement(chat)
                    summary = translations.save(str(answer.content), chat.language_name, chat.language_iso_code)
                    summaries_created += 1
                self.__di.telegram_bot_sdk.send_text_message(int(chat.external_id or "-1"), summary)
                chats_notified += 1
            except Exception as e:
                log.e(f"Announcement failed for chat #{chat.chat_id}", e)

        log.i(f"Chats: {len(target_chats)}, summaries created: {summaries_created}, notified: {chats_notified}")
        return {
            "chats_selected": len(target_chats),
            "chats_notified": chats_notified,
            "summaries_created": summaries_created,
        }

    def __create_announcement(self, target_chat: ChatConfig | None) -> AIMessage:
        target_chat = target_chat or self.__target_chat
        # TODO don't hard-code Telegram
        chat_type = ChatConfigDB.ChatType.telegram
        system_prompt = prompt_resolvers.copywriting_system_announcement(chat_type, target_chat)
        messages = [SystemMessage(system_prompt), HumanMessage(self.__raw_message)]
        response = self.__copywriter.invoke(messages)
        if not isinstance(response, AIMessage):
            raise AssertionError(f"Received a non-AI message from LLM: {response}")
        return response
