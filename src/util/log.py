import sys
import traceback
from typing import Any

from uvicorn.server import logger

from util.config import config


def _should_log(level: str) -> bool:
    if config.log_level == "local":
        return True  # we always log in local context
    levels = {"trace": 0, "debug": 1, "info": 2, "warning": 3, "error": 4}
    current_level = levels.get(config.log_level, 2)  # default to info
    request_level = levels.get(level.lower(), 2)
    return request_level >= current_level


def _format_args(*args: Any) -> tuple[str, list[Exception]]:
    exceptions = []
    formatted_parts = []

    # prepare the print components
    for arg in args:
        if isinstance(arg, Exception):
            exceptions.append(arg)
            formatted_parts.append(f"! {str(type(arg).__name__)} (see below)")
        elif hasattr(arg, "__dict__"):
            formatted_parts.append(f"{type(arg).__name__}:\n```\n{repr(arg)}\n```")
        else:
            formatted_parts.append(f"{str(arg)}")

    # edge: no message to print
    if not formatted_parts:
        return "", exceptions

    # edge: only one message line to print
    if len(formatted_parts) == 1:
        return formatted_parts[0], exceptions

    # edge: message lines are available, but no exceptions
    if not exceptions:
        head_lines = "\n ├─ ".join(formatted_parts[:-1])
        tail_line = formatted_parts[-1]
        return f"{head_lines}\n └─ {tail_line}", exceptions

    # message and exceptions are available, connect messages with a tree
    return "\n ├─ ".join(formatted_parts), exceptions


def _log_message(level: str, message: str, exceptions: list[Exception]) -> str:
    if not _should_log(level) and not exceptions:
        return message

    # for uvicorn, use the uvicorn logger
    if config.log_level != "local":
        try:
            # log the base message only if it should be logged
            if _should_log(level):
                match level:
                    case "TRACE" | "DEBUG":
                        logger.debug(message)
                    case "INFO":
                        logger.info(message)
                    case "WARN":
                        logger.warning(message)
                    case "ERROR":
                        logger.error(message)
            # log the exceptions
            for exception in exceptions:
                logger.error(f"Message: {str(exception)}")
                if trace := exception.__traceback__:
                    trace_lines = traceback.format_tb(trace)
                    indented_trace = "".join(trace_lines).strip()
                    logger.error(f"Details:\n └─ {indented_trace}")
        except Exception:
            # fallback to local printing if uvicorn logger fails
            if _should_log(level):
                print(f"[{level[0]}] {message}")
            for exception in exceptions:
                print(f" ‼  Message: {str(exception)}", file = sys.stderr)
                if trace := exception.__traceback__:
                    trace_lines = traceback.format_tb(trace)
                    indented_trace = "".join(trace_lines).strip()
                    print(indented_trace, file = sys.stderr)
        return message

    # for local execution, print to stdout/stderr
    print(f"[{level[0]}] {message}")
    for exception in exceptions:
        print(f" ‼  Message: {str(exception)}", file = sys.stderr)
        if trace := exception.__traceback__:
            trace_lines = traceback.format_tb(trace)
            indented_trace = "".join(("    " + line.strip()) for line in trace_lines)
            print(indented_trace, file = sys.stderr)
    return message


def t(*args: Any) -> str:
    message, exceptions = _format_args(*args)
    return _log_message("TRACE", message, exceptions)


def d(*args: Any) -> str:
    message, exceptions = _format_args(*args)
    return _log_message("DEBUG", message, exceptions)


def i(*args: Any) -> str:
    message, exceptions = _format_args(*args)
    return _log_message("INFO", message, exceptions)


def w(*args: Any) -> str:
    message, exceptions = _format_args(*args)
    return _log_message("WARN", message, exceptions)


def e(*args: Any) -> str:
    message, exceptions = _format_args(*args)
    return _log_message("ERROR", message, exceptions)
