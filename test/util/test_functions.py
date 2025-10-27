import unittest

from util.functions import (
    extract_url_from_replicate_result,
    first_key_with_value,
    generate_short_uuid,
    mask_secret,
    silent,
)


class FunctionsTest(unittest.TestCase):

    def test_silent_function_no_exception(self):
        @silent
        def no_exception() -> int:
            return 42

        result = no_exception()
        self.assertEqual(result, 42)

    def test_silent_function_with_exception(self):
        @silent
        def raise_exception() -> None:
            raise ValueError("This is an error")

        result = raise_exception()
        self.assertIsNone(result)

    def test_silent_lambda_no_exception(self):
        result = silent(lambda: 100)()
        self.assertEqual(result, 100)

    def test_silent_lambda_with_exception(self):
        result = silent(lambda: 10 / 0)()
        self.assertIsNone(result)

    def test_first_key_with_value_returns_correct_key(self):
        source = {1: "a", 2: "b", 3: "c"}
        value = "b"
        self.assertEqual(first_key_with_value(source, value), 2)

    def test_first_key_with_value_returns_none_for_nonexistent_value(self):
        source = {1: "a", 2: "b", 3: "c"}
        value = "d"
        self.assertIsNone(first_key_with_value(source, value))

    def test_first_key_with_value_returns_none_for_empty_dict(self):
        source = {}
        value = "a"
        self.assertIsNone(first_key_with_value(source, value))

    def test_first_key_with_value_returns_first_key_for_duplicate_values(self):
        source = {1: "a", 2: "b", 3: "b"}
        value = "b"
        self.assertEqual(first_key_with_value(source, value), 2)

    def test_mask_secret_none(self):
        # noinspection HardcodedPassword
        secret = None
        result = mask_secret(secret)
        self.assertEqual(result, None)

    def test_mask_secret_empty_string(self):
        # noinspection HardcodedPassword
        secret = ""
        result = mask_secret(secret)
        self.assertEqual(result, "")

    def test_mask_secret_single_char(self):
        # noinspection HardcodedPassword
        secret = "a"
        result = mask_secret(secret)
        self.assertEqual(result, "*")

    def test_mask_secret_two_chars(self):
        # noinspection HardcodedPassword
        secret = "ab"
        result = mask_secret(secret)
        self.assertEqual(result, "**")

    def test_mask_secret_three_chars(self):
        # noinspection HardcodedPassword
        secret = "abc"
        result = mask_secret(secret)
        self.assertEqual(result, "***")

    def test_mask_secret_four_chars(self):
        # noinspection HardcodedPassword
        secret = "abcd"
        result = mask_secret(secret)
        self.assertEqual(result, "****")

    def test_mask_secret_medium_length_short(self):
        # noinspection HardcodedPassword
        secret = "abcde"
        result = mask_secret(secret)
        self.assertEqual(result, "a***e")

    def test_mask_secret_medium_length_long(self):
        # noinspection HardcodedPassword
        secret = "abcdefgh"
        result = mask_secret(secret)
        self.assertEqual(result, "a******h")

    def test_mask_secret_large_length_short(self):
        # noinspection HardcodedPassword
        secret = "abcdefghi"
        result = mask_secret(secret)
        self.assertEqual(result, "abc*****ghi")

    def test_mask_secret_large_length_long(self):
        # noinspection HardcodedPassword
        secret = "abcdefghijklmnopqrstuvwxyz"
        result = mask_secret(secret)
        self.assertEqual(result, "abc*****xyz")

    def test_mask_secret_custom_mask(self):
        # noinspection HardcodedPassword
        secret = "abcdefghijklmnopqrstuvwxyz"
        result = mask_secret(secret, mask = "#")
        self.assertEqual(result, "abc#####xyz")

    def test_generate_short_uuid_length(self):
        result = generate_short_uuid()
        self.assertEqual(len(result), 8)

    def test_generate_short_uuid_format(self):
        result = generate_short_uuid()
        # Should only contain hexadecimal characters
        self.assertRegex(result, r"^[0-9a-f]{8}$")

    def test_generate_deterministic_short_uuid_consistency(self):
        from util.functions import generate_deterministic_short_uuid
        seed = "test_file_id_123"
        result1 = generate_deterministic_short_uuid(seed)
        result2 = generate_deterministic_short_uuid(seed)
        self.assertEqual(result1, result2)

    def test_generate_deterministic_short_uuid_format(self):
        from util.functions import generate_deterministic_short_uuid
        result = generate_deterministic_short_uuid("test_seed")
        self.assertEqual(len(result), 8)
        # Should only contain hexadecimal characters
        self.assertRegex(result, r"^[0-9a-f]{8}$")

    def test_generate_deterministic_short_uuid_different_seeds(self):
        from util.functions import generate_deterministic_short_uuid
        result1 = generate_deterministic_short_uuid("seed1")
        result2 = generate_deterministic_short_uuid("seed2")
        self.assertNotEqual(result1, result2)

    def test_generate_deterministic_short_uuid_realistic_telegram_ids(self):
        from util.functions import generate_deterministic_short_uuid
        # Test with realistic Telegram file IDs
        telegram_file_id = "BAADBQADBgADmEjNSW5XPx5aVTaiAg"
        result1 = generate_deterministic_short_uuid(telegram_file_id)
        result2 = generate_deterministic_short_uuid(telegram_file_id)

        # Should be consistent
        self.assertEqual(result1, result2)
        # Should be valid format
        self.assertEqual(len(result1), 8)
        self.assertRegex(result1, r"^[0-9a-f]{8}$")

    def test_extract_url_from_replicate_result_list_with_file_output(self):
        class MockFileOutput:

            url = "https://example.com/image.png"

        result = extract_url_from_replicate_result([MockFileOutput()])
        self.assertEqual(result, "https://example.com/image.png")

    def test_extract_url_from_replicate_result_list_with_string(self):
        result = extract_url_from_replicate_result(["https://example.com/image.png"])
        self.assertEqual(result, "https://example.com/image.png")

    def test_extract_url_from_replicate_result_single_file_output(self):
        class MockFileOutput:

            url = "https://example.com/image.png"

        result = extract_url_from_replicate_result(MockFileOutput())
        self.assertEqual(result, "https://example.com/image.png")

    def test_extract_url_from_replicate_result_single_string(self):
        result = extract_url_from_replicate_result("https://example.com/image.png")
        self.assertEqual(result, "https://example.com/image.png")

    def test_extract_url_from_replicate_result_empty_list(self):
        with self.assertRaises(ValueError) as context:
            extract_url_from_replicate_result([])
        self.assertIn("Empty result list", str(context.exception))

    def test_extract_url_from_replicate_result_unexpected_type_in_list(self):
        with self.assertRaises(ValueError) as context:
            extract_url_from_replicate_result([12345])
        self.assertIn("Unexpected result type in list", str(context.exception))

    def test_extract_url_from_replicate_result_unexpected_type(self):
        with self.assertRaises(ValueError) as context:
            extract_url_from_replicate_result(12345)
        self.assertIn("Unexpected result type from Replicate", str(context.exception))

    def test_normalize_phone_number_none(self):
        from util.functions import normalize_phone_number
        self.assertIsNone(normalize_phone_number(None))

    def test_normalize_phone_number_empty(self):
        from util.functions import normalize_phone_number
        self.assertEqual(normalize_phone_number(""), "")

    def test_normalize_phone_number_plus_and_dashes(self):
        from util.functions import normalize_phone_number
        self.assertEqual(normalize_phone_number("+1-234-567-8900"), "12345678900")

    def test_normalize_phone_number_spaces_parentheses(self):
        from util.functions import normalize_phone_number
        self.assertEqual(normalize_phone_number("(123) 456 7890"), "1234567890")

    def test_normalize_phone_number_mixed_chars(self):
        from util.functions import normalize_phone_number
        self.assertEqual(normalize_phone_number("wa:+38 044-123-45-67 ext.89"), "38044123456789")

    def test_normalize_username_none(self):
        from util.functions import normalize_username
        self.assertIsNone(normalize_username(None))

    def test_normalize_username_empty(self):
        from util.functions import normalize_username
        self.assertEqual(normalize_username(""), "")

    def test_normalize_username_with_at(self):
        from util.functions import normalize_username
        self.assertEqual(normalize_username("@username"), "username")

    def test_normalize_username_with_plus(self):
        from util.functions import normalize_username
        self.assertEqual(normalize_username("+username"), "username")

    def test_normalize_username_with_spaces(self):
        from util.functions import normalize_username
        self.assertEqual(normalize_username("user name"), "username")

    def test_normalize_username_mixed_chars(self):
        from util.functions import normalize_username
        self.assertEqual(normalize_username("@ +user name+"), "username")
