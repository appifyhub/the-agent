import random
import time
from threading import Event, Lock, Thread

from db.schema.chat_config import ChatConfig
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

DEFAULT_REACTION_INTERVAL_S = 15
DEFAULT_TEXT_UPDATE_INTERVAL_S = 45
TYPING_STATUS_INTERVAL_S = 5  # set by Telegram API for auto-clearing
MAX_CYCLES = int((10 * DEFAULT_TEXT_UPDATE_INTERVAL_S) / TYPING_STATUS_INTERVAL_S)  # announce 10 delays max

# subset of features.prompting.prompt_library.ALLOWED_TELEGRAM_EMOJIS
# sorted by intensity (later ones emote more about the delay)
ESCALATING_REACTIONS = [
    "🫡", "👨‍💻", "⚡", "🔥", "👀", "🤔", "🤨",
    "😐", "🥱", "😴", "🥴", "😨", "😱", "🤯",
    "😢", "😭", "🙈", "💩", "💅",
]


class TelegramProgressNotifier(SafePrinterMixin):
    __chat_config: ChatConfig
    __message_id: str
    __last_reaction_time: float
    __last_text_update_time: float
    __next_reaction_index: int
    __total_cycles: int
    __lock: Lock
    __thread: Thread | None
    __signal: Event
    __bot_sdk: TelegramBotSDK

    def __init__(
        self,
        chat_config: ChatConfig,
        message_id: str,
        bot_sdk: TelegramBotSDK,
        auto_start: bool = False,
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
        self.__bot_sdk = bot_sdk
        if auto_start:
            self.start()
        self.sprint(f"Text update interval: {self.__text_update_interval_s}")

    def start(self):
        self.sprint("Acquiring start lock...")
        if self.__thread and self.__thread.is_alive():
            self.sprint(f"  Thread {self.__thread.name} is already running (before lock)")
            return
        with self.__lock:
            self.sprint("  Acquired")
            if self.__thread and self.__thread.is_alive():
                self.sprint(f"  Thread {self.__thread.name} is already running (after lock)")
                return
            self.sprint("  Starting a new thread...")
            self.__signal.clear()
            thread_name = f"telegram-progress-notifier-{random.randint(1000, 9999)}"
            self.__thread = Thread(name = thread_name, target = self.__run, daemon = True)
            self.__thread.start()  # fire and forget
            self.sprint(f"  Started thread {thread_name}")

    def stop(self):
        self.sprint("Acquiring stop lock...")
        if not self.__thread:
            self.sprint("  No thread running (before lock)")
            return
        with self.__lock:
            self.sprint("  Acquired")
            self.sprint(f"  Stopping thread {self.__thread.name}...")
            self.__signal.set()
            if not self.__thread:
                self.sprint("  No thread running (after lock)")
                return
            self.__thread.join(timeout = 1)  # wait for up to 1 second and proceed anyway
            if self.__thread.is_alive():
                self.sprint("  Thread did not stop in time, proceeding...")
                self.__total_cycles = MAX_CYCLES
            self.sprint(f"  Stopped thread {self.__thread.name}")
        # noinspection TryExceptPass
        # remove the stale reaction (sometimes fails due to API race condition but doesn't matter)
        try:
            self.__bot_sdk.set_reaction(self.__chat_config.chat_id, self.__message_id, None)
        except:  # noqa: E722
            pass

    def __run(self):
        current_time_s = time.time()
        self.__last_reaction_time = current_time_s
        self.__last_text_update_time = current_time_s

        while not self.__signal.is_set() and self.__total_cycles < MAX_CYCLES:
            current_time_s = time.time()
            reaction_elapsed_s = current_time_s - self.__last_reaction_time
            text_update_elapsed_s = current_time_s - self.__last_text_update_time

            if text_update_elapsed_s >= float(self.__text_update_interval_s):
                # it takes a long time, let's track it
                elapsed_time_total_s = time.time() - self.__last_text_update_time
                elapsed_time_m, elapsed_time_s = divmod(int(elapsed_time_total_s), 60)
                elapse_time_text = f"{elapsed_time_m} min[s] {elapsed_time_s} sec[s]"
                self.sprint(f"  Text update interval: {elapse_time_text}")
                self.__last_text_update_time = current_time_s
            elif reaction_elapsed_s >= float(self.__reaction_interval_s):
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
                self.__bot_sdk.set_status_uploading_image(self.__chat_config.chat_id)
            else:
                self.__bot_sdk.set_status_typing(self.__chat_config.chat_id)
        except Exception as e:
            self.sprint(f"Failed to set \"{status}\" status", e)

    def __send_reaction(self):
        self.sprint("Time for a reaction update")
        self.__set_chat_status(is_long = False)
        try:
            next_reaction = ESCALATING_REACTIONS[self.__next_reaction_index]
            self.__next_reaction_index = (self.__next_reaction_index + 1) % len(ESCALATING_REACTIONS)
            self.__bot_sdk.set_reaction(self.__chat_config.chat_id, self.__message_id, next_reaction)
        except Exception as e:
            self.sprint(f"Failed to send reaction: {e}")
