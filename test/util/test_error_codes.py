import inspect
import unittest

from util import error_codes


class ErrorCodesTest(unittest.TestCase):

    def test_no_duplicate_error_codes(self):
        members = inspect.getmembers(error_codes)
        constants = {
            name: value
            for name, value in members
            if not name.startswith("_") and isinstance(value, int)
        }
        seen: dict[int, str] = {}
        duplicates: list[str] = []
        for name, value in constants.items():
            if value in seen:
                duplicates.append(f"{name}={value} duplicates {seen[value]}")
            else:
                seen[value] = name
        self.assertEqual(duplicates, [], f"Duplicate error codes found: {duplicates}")

    def test_error_codes_in_valid_category_ranges(self):
        valid_ranges = [
            (1000, 1999),  # Validation
            (2000, 2999),  # Not Found
            (3000, 3999),  # Authorization
            (4000, 4999),  # Authentication
            (5000, 5999),  # External Service
            (6000, 6999),  # Rate Limit
            (7000, 7999),  # Configuration
            (8000, 8999),  # Internal
        ]
        members = inspect.getmembers(error_codes)
        constants = {
            name: value
            for name, value in members
            if not name.startswith("_") and isinstance(value, int)
        }
        for name, value in constants.items():
            in_range = any(low <= value <= high for low, high in valid_ranges)
            self.assertTrue(in_range, f"{name}={value} is not in any valid category range")
