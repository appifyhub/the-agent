import random
import time
from datetime import datetime
from threading import Thread, Lock, Event

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage

from db.crud.chat_message import ChatMessageCRUD
from db.schema.chat_config import ChatConfig
from db.schema.chat_message import ChatMessageSave
from features.chat.telegram.telegram_bot_api import TelegramBotAPI
from features.prompting import prompt_library
from util.config import config
from util.functions import construct_bot_message_id
from util.safe_printer_mixin import SafePrinterMixin

DEFAULT_REACTION_INTERVAL_S = 15
DEFAULT_TEXT_UPDATE_INTERVAL_S = 45
TYPING_STATUS_INTERVAL_S = 5  # set by Telegram API for auto-clearing
MAX_CYCLES = int((10 * DEFAULT_TEXT_UPDATE_INTERVAL_S) / TYPING_STATUS_INTERVAL_S)  # announce 10 delays max

ANTHROPIC_AI_MODEL = "claude-3-5-sonnet-20240620"
ANTHROPIC_AI_TEMPERATURE = 0.5
ANTHROPIC_MAX_TOKENS = 500

# subset of features.prompting.prompt_library.ALLOWED_TELEGRAM_EMOJIS
# sorted by intensity (later ones emote more about the delay)
ESCALATING_REACTIONS = [
    "🫡", "👨‍💻", "⚡", "🔥", "👀", "🤔",
    "🤨", "😐", "🥱", "😴", "🥴", "😨",
    "😱", "🤯", "😢", "😭", "🙈", "💩",
    "💅",
]


class TelegramProgressNotifier(SafePrinterMixin):
    __chat_config: ChatConfig
    __message_id: str
    __last_reaction_time: float
    __last_text_update_time: float
    __next_reaction_index: int
    __total_cycles: int
    __llm: BaseChatModel
    __llm_input: list[BaseMessage]
    __lock: Lock
    __thread: Thread | None
    __signal: Event
    __bot_api: TelegramBotAPI
    __chat_message_dao: ChatMessageCRUD

    def __init__(
        self,
        chat_config: ChatConfig,
        message_id: str,
        bot_api: TelegramBotAPI,
        chat_message_dao: ChatMessageCRUD,
        auto_start: bool = True,
        reaction_interval_s: int = DEFAULT_REACTION_INTERVAL_S,
        text_update_interval_s: int = DEFAULT_TEXT_UPDATE_INTERVAL_S,
    ):
        super().__init__(config.verbose)
        self.__chat_config = chat_config
        self.__message_id = message_id
        self.__last_reaction_time = 0
        self.__last_text_update_time = 0
        self.__next_reaction_index = 0
        self.__total_cycles = 0
        self.__thread = None
        self.__lock = Lock()
        self.__signal = Event()
        self.__reaction_interval_s = reaction_interval_s
        self.__text_update_interval_s = text_update_interval_s
        # noinspection PyArgumentList
        self.__llm = ChatAnthropic(
            model_name = ANTHROPIC_AI_MODEL,
            temperature = ANTHROPIC_AI_TEMPERATURE,
            max_tokens = ANTHROPIC_MAX_TOKENS,
            timeout = float(config.web_timeout_s),
            max_retries = config.web_retries,
            api_key = str(config.anthropic_token),
        )
        prompt = prompt_library.translator_on_response(
            base_prompt = prompt_library.announcer_event_telegram,
            language_name = self.__chat_config.language_name,
            language_iso_code = self.__chat_config.language_iso_code,
        )
        self.__llm_input = [SystemMessage(prompt)]
        self.__bot_api = bot_api
        self.__chat_message_dao = chat_message_dao
        if auto_start:
            self.start()
        print(f"Text update interval: {self.__text_update_interval_s}")

    def start(self):
        self.sprint("Acquiring start lock...")
        with self.__lock:
            self.sprint("  Acquired")
            if self.__thread and self.__thread.is_alive():
                self.sprint(f"  Thread {self.__thread.name} is already running")
                return
            self.sprint("  Starting a new thread...")
            self.__signal.clear()
            thread_name = f"telegram-progress-notifier-{random.randint(1000, 9999)}"
            self.__thread = Thread(name = thread_name, target = self.__run, daemon = True)
            self.__thread.start()  # fire and forget
            self.sprint(f"  Started thread {thread_name}")

    def stop(self):
        self.sprint("Acquiring stop lock...")
        with self.__lock:
            self.sprint("  Acquired")
            self.sprint(f"  Stopping thread {self.__thread.name}...")
            self.__signal.set()
            if not self.__thread:
                self.sprint("  No thread running")
                return
            self.__thread.join(timeout = 1)  # wait for up to 1 second and proceed anyway
            if self.__thread.is_alive():
                self.sprint("  Thread did not stop in time, proceeding...")
                self.__total_cycles = MAX_CYCLES
            self.sprint(f"  Stopped thread {self.__thread.name}")
        # remove the stale reaction
        self.__bot_api.set_reaction(self.__chat_config.chat_id, self.__message_id, None)

    def __run(self):
        current_time_s = time.time()
        self.__last_reaction_time = current_time_s
        self.__last_text_update_time = current_time_s

        while not self.__signal.is_set() and self.__total_cycles < MAX_CYCLES:
            current_time_s = time.time()
            reaction_elapsed_s = current_time_s - self.__last_reaction_time
            text_update_elapsed_s = current_time_s - self.__last_text_update_time

            if text_update_elapsed_s >= self.__text_update_interval_s:
                # check if a message update is needed
                self.__send_message()
                self.__last_text_update_time = current_time_s
            elif reaction_elapsed_s >= self.__reaction_interval_s:
                # check if reaction update is needed
                self.__send_reaction()
                self.__last_reaction_time = current_time_s
            else:
                # no updates, keep the status running (else Telegram will clear it)
                self.__set_chat_status(is_long = False)

            self.__total_cycles += 1
            self.__signal.wait(TYPING_STATUS_INTERVAL_S)

    def __set_chat_status(self, is_long: bool):
        status = "uploading" if is_long else "typing"
        self.sprint(f"Setting \"{status}\" status")
        try:
            if is_long:
                self.__bot_api.set_status_uploading_image(self.__chat_config.chat_id)
            else:
                self.__bot_api.set_status_typing(self.__chat_config.chat_id)
        except Exception as e:
            self.sprint(f"Failed to set \"{status}\" status", e)

    def __send_reaction(self):
        self.sprint("Time for a reaction update")
        self.__set_chat_status(is_long = False)
        try:
            next_reaction = ESCALATING_REACTIONS[self.__next_reaction_index]
            self.__next_reaction_index = (self.__next_reaction_index + 1) % len(ESCALATING_REACTIONS)
            self.__bot_api.set_reaction(self.__chat_config.chat_id, self.__message_id, next_reaction)
        except Exception as e:
            self.sprint(f"Failed to send reaction: {e}")

    def __send_message(self):
        self.sprint("Time for a message update")
        self.__set_chat_status(is_long = True)
        try:
            # prepare the message contents
            elapsed_time_total_s = time.time() - self.__last_text_update_time
            elapsed_time_m, elapsed_time_s = divmod(int(elapsed_time_total_s), 60)
            elapse_time_text = f"{elapsed_time_m} min[s] {elapsed_time_s} sec[s]"
            text_update = f"""
                [To the user, your buddy]
                Your requested operation is in it's work cycle number-{self.__total_cycles}.
                You've been waiting {elapse_time_text} already, and I know mate - it really sucks.
                I hope your request won't take much longer to complete. I apologize.
                Wait a while longer and I'll get back to you!
            """.strip()

            # fetch the actual message viable for sending
            messages = self.__llm_input.copy()
            messages.append(HumanMessage(text_update))
            response = self.__llm.invoke(messages)
            if not isinstance(response, AIMessage) or not response.content:
                raise ValueError(f"Got a complex AI response: {response}")

            # get rid of the old reaction
            self.__bot_api.set_reaction(self.__chat_config.chat_id, self.__message_id, None)
            # send the actual message
            message_to_send = str(response.content)
            self.__bot_api.send_text_message(self.__chat_config.chat_id, message_to_send)
            # and store the new text
            sent_at = datetime.now()
            message_to_store = ChatMessageSave(
                chat_id = self.__chat_config.chat_id,
                message_id = construct_bot_message_id(self.__chat_config.chat_id, sent_at),
                author_id = prompt_library.TELEGRAM_BOT_USER.id,
                sent_at = sent_at,
                text = message_to_send,
            )
            self.__chat_message_dao.save(message_to_store)
        except Exception as e:
            self.sprint("Failed to send message", e)
