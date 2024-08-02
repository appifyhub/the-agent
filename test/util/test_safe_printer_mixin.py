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

    def test_safe_print_with_exception_verbose(self):
        printer = SafePrinterMixin(verbose = True)

        def function_that_raises_exception():
            raise ValueError("Test exception")

        try:
            function_that_raises_exception()
        except ValueError as e:
            with patch("sys.stdout", new = StringIO()) as stdout_mock, \
                patch("sys.stderr", new = StringIO()) as stderr_mock:
                printer.sprint("Error occurred", e)
                stdout_output = stdout_mock.getvalue()
                stderr_output = stderr_mock.getvalue()

                self.assertIn("Error occurred", stdout_output)
                self.assertIn("Test exception", stdout_output)
                self.assertIn("Traceback (most recent call last):", stderr_output)
                self.assertIn("ValueError: Test exception", stderr_output)
                self.assertIn("function_that_raises_exception", stderr_output)

    def test_safe_print_with_exception_non_verbose(self):
        printer = SafePrinterMixin(verbose = False)
        test_exception = ValueError("Test exception")
        with patch("sys.stdout", new = StringIO()) as stdout_mock, \
            patch("sys.stderr", new = StringIO()) as stderr_mock:
            printer.sprint("Error occurred", test_exception)
            self.assertEqual(stdout_mock.getvalue(), "")
            self.assertEqual(stderr_mock.getvalue(), "")
