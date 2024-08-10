import traceback

from uvicorn.server import logger

from util.config import config


class SafePrinterMixin:
    __verbose: bool

    def __init__(self, verbose: bool = False):
        self.__verbose = verbose

    def sprint(self, content: str, e: Exception | None = None):
        """
        Safely ('s') prints the contents if the verbose flag is set to True.

        Parameters:
        content (str): The content to be printed.
        e (Exception | None): The exception to be printed, if available.
        """
        if self.__verbose:
            if e:
                logger.warning(content)
                logger.error(str(e))
                traceback.print_exc()
            else:
                logger.debug(content)


def sprint(content: str, e: Exception | None = None):
    """
    Safely ('s') prints the contents if the verbose flag is set to True in config.

    Parameters:
    content (str): The content to be printed.
    e (Exception | None): The exception to be printed, if available.
    """
    if config.verbose:
        if e:
            logger.warning(content)
            logger.error(str(e))
            traceback.print_exc()
        else:
            logger.debug(content)
