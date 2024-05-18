import unittest
from io import StringIO
from unittest.mock import patch

from util.safe_printer_mixin import SafePrinterMixin


class SafePrinterMixinTest(unittest.TestCase):

    def test_safe_print_verbose(self):
        printer = SafePrinterMixin(verbose = True)
        with patch("sys.stdout", new = StringIO()) as mock:
            printer.sprint("Test")
            self.assertEqual(mock.getvalue(), "Test\n")

    def test_safe_print_non_verbose(self):
        printer = SafePrinterMixin(verbose = False)
        with patch("sys.stdout", new = StringIO()) as mock:
            printer.sprint("Test")
            self.assertEqual(mock.getvalue(), "")
