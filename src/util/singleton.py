import threading


class Singleton(type):
    _instances = {}
    _lock = threading.Lock()  # Lock object to ensure thread-safety

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
