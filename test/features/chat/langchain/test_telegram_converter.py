import unittest
from datetime import date
from uuid import UUID

from langchain_core.messages import HumanMessage, AIMessage

from db.schema.chat_message import ChatMessage
from db.schema.user import User
from features.chat.langchain.telegram_converter import TelegramConverter
from util.config import config


class TelegramConverterTest(unittest.TestCase):
    __converter: TelegramConverter

    def setUp(self):
        config.verbose = True
        self.__converter = TelegramConverter()

    def test_convert_message_with_author(self):
        author = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_user_id = 12345,
            telegram_username = "john_doe",
            full_name = "John Doe",
        )
        message = ChatMessage(chat_id = "c1", message_id = "m1", text = "Hello, how are you?")
        expected_output = HumanMessage("@john_doe [John Doe]:\nHello, how are you?")
        self.assertEqual(self.__converter.convert(author, message), expected_output)

    def test_convert_message_slim_author(self):
        author = User(id = UUID(int = 1), created_at = date.today(), telegram_user_id = 12345)
        message = ChatMessage(chat_id = "c1", message_id = "m1", text = "Test message")
        expected_output = HumanMessage("@12345:\nTest message")
        self.assertEqual(self.__converter.convert(author, message), expected_output)

    def test_convert_message_ai_author(self):
        ai_author = User(
            id = UUID(int = 2),
            created_at = date.today(),
            telegram_user_id = 67890,
            telegram_username = config.telegram_bot_username,
            full_name = config.telegram_bot_name,
        )
        message = ChatMessage(chat_id = "c2", message_id = "m2", text = "I'm an AI assistant.")
        expected_output = AIMessage("I'm an AI assistant.")
        self.assertEqual(self.__converter.convert(ai_author, message), expected_output)

    def test_convert_message_no_author(self):
        message = ChatMessage(chat_id = "c1", message_id = "m1", text = "Test message")
        expected_output = AIMessage("Test message")
        self.assertEqual(self.__converter.convert(None, message), expected_output)
