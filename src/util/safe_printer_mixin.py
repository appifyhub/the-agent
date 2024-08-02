import traceback


class SafePrinterMixin:
    __verbose: bool = False

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
            print(content)
            if e:
                print(str(e))
                if self.__verbose:
                    traceback.print_exc()
