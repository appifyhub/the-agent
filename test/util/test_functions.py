import unittest
from datetime import date, datetime
from uuid import UUID

from db.model.chat_config import ChatConfigDB
from db.schema.user import User, UserSave
from features.integrations.integrations import resolve_agent_user
from util.functions import construct_bot_message_id, first_key_with_value, generate_short_uuid, is_the_agent, mask_secret, silent


class FunctionsTest(unittest.TestCase):

    agent_user: UserSave

    def setUp(self):
        self.agent_user = resolve_agent_user(ChatConfigDB.ChatType.telegram)

    def test_is_the_agent_true(self):
        self.agent_user.telegram_username = "the_new_agent"
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "the_new_agent",
        )
        self.assertTrue(is_the_agent(user))

    def test_is_the_agent_false(self):
        self.agent_user.telegram_username = "the_not_agent"
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "the_new_agent",
        )
        self.assertFalse(is_the_agent(user))

    def test_is_the_agent_none(self):
        self.assertFalse(is_the_agent(None))

    def test_output_format(self):
        chat_id = UUID("7921acbe-a9d3-432b-8a6e-86ac9953405b")
        sent_at = datetime(2023, 5, 15, 10, 30, 45)
        result = construct_bot_message_id(chat_id, sent_at)
        self.assertRegex(result, r"^7921acbe-a9d3-432b-8a6e-86ac9953405b-230515103045-\d{4}$")

    def test_different_chat_ids(self):
        chat_id_1 = UUID("7921acbe-a9d3-432b-8a6e-86ac9953405b")
        chat_id_2 = UUID("9a2e1c5b-ef5d-4c84-9d63-5c090eef4f5f")
        sent_at = datetime(2023, 5, 15, 10, 30, 45)
        result1 = construct_bot_message_id(chat_id_1, sent_at)
        result2 = construct_bot_message_id(chat_id_2, sent_at)
        self.assertNotEqual(result1, result2)
        self.assertTrue(result1.startswith("7921acbe-a9d3-432b-8a6e-86ac9953405b-"))
        self.assertTrue(result2.startswith("9a2e1c5b-ef5d-4c84-9d63-5c090eef4f5f-"))

    def test_different_timestamps(self):
        chat_id = UUID("7921acbe-a9d3-432b-8a6e-86ac9953405b")
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
