import unittest
from datetime import date, datetime
from uuid import UUID

from db.schema.user import User
from features.prompting.prompt_library import TELEGRAM_BOT_USER
from util.functions import is_the_agent, construct_bot_message_id, silent, first_key_with_value, mask_secret


class FunctionsTest(unittest.TestCase):

    def test_is_the_agent_true(self):
        TELEGRAM_BOT_USER.telegram_username = "the_new_agent"
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "the_new_agent",
        )
        self.assertTrue(is_the_agent(user))

    def test_is_the_agent_false(self):
        TELEGRAM_BOT_USER.telegram_username = "the_not_agent"
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "the_new_agent",
        )
        self.assertFalse(is_the_agent(user))

    def test_is_the_agent_none(self):
        self.assertFalse(is_the_agent(None))

    def test_output_format(self):
        chat_id = "chat123"
        sent_at = datetime(2023, 5, 15, 10, 30, 45)
        result = construct_bot_message_id(chat_id, sent_at)
        self.assertRegex(result, r"^chat123-230515103045-\d{4}$")

    def test_different_chat_ids(self):
        sent_at = datetime(2023, 5, 15, 10, 30, 45)
        result1 = construct_bot_message_id("chat1", sent_at)
        result2 = construct_bot_message_id("chat2", sent_at)
        self.assertNotEqual(result1, result2)
        self.assertTrue(result1.startswith("chat1-"))
        self.assertTrue(result2.startswith("chat2-"))

    def test_different_timestamps(self):
        chat_id = "chat123"
        sent_at1 = datetime(2023, 5, 15, 10, 30, 45)
        sent_at2 = datetime(2023, 5, 15, 10, 30, 46)
        result1 = construct_bot_message_id(chat_id, sent_at1)
        result2 = construct_bot_message_id(chat_id, sent_at2)
        self.assertNotEqual(result1, result2)
        self.assertNotEqual(result1[-9:-5], result2[-9:-5])

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
