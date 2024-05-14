class SafePrinterMixin:
    __verbose: bool = False

    def __init__(self, verbose: bool = False):
        self.__verbose = verbose

    def sprint(self, content: str):
        """
        Safely ('s') prints the contents if the verbose flag is set to True.

        Parameters:
        content (str): The content to be printed.
        """
        if self.__verbose:
            print(content)
