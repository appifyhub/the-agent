import unittest
from unittest.mock import patch

from util.safe_printer_mixin import SafePrinterMixin


class SafePrinterMixinTest(unittest.TestCase):

    @patch("util.safe_printer_mixin.logger")
    def test_sprint_verbose(self, mock_logger):
        printer = SafePrinterMixin(verbose = True)
        printer.sprint("Test")
        mock_logger.debug.assert_called_once_with("Test")

    @patch("util.safe_printer_mixin.logger")
    def test_sprint_non_verbose(self, mock_logger):
        printer = SafePrinterMixin(verbose = False)
        printer.sprint("Test")
        mock_logger.debug.assert_not_called()

    @patch("util.safe_printer_mixin.logger")
    @patch("util.safe_printer_mixin.traceback")
    def test_sprint_with_exception_verbose(self, mock_traceback, mock_logger):
        printer = SafePrinterMixin(verbose = True)
        test_exception = ValueError("Test exception")
        printer.sprint("Error occurred", test_exception)

        mock_logger.warning.assert_called_once_with("Error occurred")
        mock_logger.error.assert_called_once_with(str(test_exception))
        mock_traceback.print_exc.assert_called_once()

    @patch("util.safe_printer_mixin.logger")
    @patch("util.safe_printer_mixin.traceback")
    def test_sprint_with_exception_non_verbose(self, mock_traceback, mock_logger):
        printer = SafePrinterMixin(verbose = False)
        test_exception = ValueError("Test exception")
        printer.sprint("Error occurred", test_exception)

        mock_logger.debug.assert_not_called()
        mock_logger.warning.assert_not_called()
        mock_traceback.print_exc.assert_not_called()
