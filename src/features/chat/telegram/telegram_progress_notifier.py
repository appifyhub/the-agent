import random
import time
from threading import Event, Lock, Thread

from di.di import DI
from util import log

DEFAULT_REACTION_INTERVAL_S = 15
DEFAULT_TEXT_UPDATE_INTERVAL_S = 45
TYPING_STATUS_INTERVAL_S = 5  # set by Telegram API for auto-clearing
MAX_CYCLES = int((10 * DEFAULT_TEXT_UPDATE_INTERVAL_S) / TYPING_STATUS_INTERVAL_S)  # announce 10 delays max

# subset of features.integrations.integrations_config.TELEGRAM_REACTIONS
# sorted by intensity (later ones emote more about the delay)
ESCALATING_REACTIONS = [
    "🫡", "👨‍💻", "⚡", "🔥", "👀", "🤔", "🤨",
    "😐", "🥱", "😴", "🥴", "😨", "😱", "🤯",
    "😢", "😭", "🙈", "💩", "💅",
]


class TelegramProgressNotifier:

    __message_id: str
    __last_reaction_time: float
    __last_text_update_time: float
    __next_reaction_index: int
    __total_cycles: int
    __lock: Lock
    __thread: Thread | None
    __signal: Event
    __di: DI

    def __init__(
        self,
        message_id: str,
        di: DI,
        auto_start: bool = False,
        reaction_interval_s: int = DEFAULT_REACTION_INTERVAL_S,
        text_update_interval_s: int = DEFAULT_TEXT_UPDATE_INTERVAL_S,
    ):
        self.__di = di
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
        if auto_start:
            self.start()
        log.d(f"Text update interval: {self.__text_update_interval_s}")

    def start(self):
        log.d("Acquiring start lock...")
        if self.__thread and self.__thread.is_alive():
            log.d(f"  Thread {self.__thread.name} is already running (before lock)")
            return
        with self.__lock:
            log.t("  Acquired")
            if self.__thread and self.__thread.is_alive():
                log.d(f"  Thread {self.__thread.name} is already running (after lock)")
                return
            log.t("  Starting a new thread...")
            self.__signal.clear()
            thread_name = f"telegram-progress-notifier-{random.randint(1000, 9999)}"
            self.__thread = Thread(name = thread_name, target = self.__run, daemon = True)
            self.__thread.start()  # fire and forget
            log.t(f"  Started thread {thread_name}")

    def stop(self):
        log.t("Acquiring stop lock...")
        if not self.__thread:
            log.t("  No thread running (before lock)")
            return
        with self.__lock:
            log.t("  Acquired")
            log.t(f"  Stopping thread {self.__thread.name}...")
            self.__signal.set()
            if not self.__thread:
                log.t("  No thread running (after lock)")
                return
            self.__thread.join(timeout = 1)  # wait for up to 1 second and proceed anyway
            if self.__thread.is_alive():
                log.t("  Thread did not stop in time, proceeding...")
                self.__total_cycles = MAX_CYCLES
            log.t(f"  Stopped thread {self.__thread.name}")
        # noinspection TryExceptPass
        # remove the stale reaction (sometimes fails due to API race condition but doesn't matter)
        try:
            self.__di.telegram_bot_sdk.set_reaction(str(self.__di.require_invoker_chat().external_id), self.__message_id, None)
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
                log.t(f"  Text update interval: {elapse_time_text}")
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
        log.t(f"Setting \"{status}\" status")
        try:
            invoker_chat = self.__di.require_invoker_chat()
            if is_long:
                self.__di.telegram_bot_sdk.set_status_uploading_image(str(invoker_chat.external_id))
            else:
                self.__di.telegram_bot_sdk.set_status_typing(str(invoker_chat.external_id))
        except Exception as e:
            log.w(f"Failed to set \"{status}\" status", e)

    def __send_reaction(self):
        log.t("Time for a reaction update")
        self.__set_chat_status(is_long = False)
        try:
            invoker_chat = self.__di.require_invoker_chat()
            next_reaction = ESCALATING_REACTIONS[self.__next_reaction_index]
            self.__next_reaction_index = (self.__next_reaction_index + 1) % len(ESCALATING_REACTIONS)
            self.__di.telegram_bot_sdk.set_reaction(str(invoker_chat.external_id), self.__message_id, next_reaction)
        except Exception as e:
            log.w(f"Failed to send reaction: {e}")
