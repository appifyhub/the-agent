import unittest
from datetime import date
from uuid import UUID

from langchain_core.messages import HumanMessage, AIMessage

from db.schema.chat_message import ChatMessage
from db.schema.user import User
from features.chat.telegram.langchain_telegram_mapper import LangChainTelegramMapper
from features.prompting.predefined_prompts import MULTI_MESSAGE_DELIMITER, TELEGRAM_BOT_USER
from util.config import config


class LangChainTelegramMapperTest(unittest.TestCase):
    __mapper: LangChainTelegramMapper

    def setUp(self):
        config.verbose = True
        self.__mapper = LangChainTelegramMapper()

    def test_map_to_langchain_with_author(self):
        author = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_user_id = 12345,
            telegram_username = "john_doe",
            full_name = "John Doe",
        )
        message = ChatMessage(chat_id = "c1", message_id = "m1", text = "Hello, how are you?")
        expected_output = HumanMessage("@john_doe [John Doe]:\nHello, how are you?")
        self.assertEqual(self.__mapper.map_to_langchain(author, message), expected_output)

    def test_map_to_langchain_with_slim_author(self):
        author = User(id = UUID(int = 1), created_at = date.today(), telegram_user_id = 12345)
        message = ChatMessage(chat_id = "c1", message_id = "m1", text = "Test message")
        expected_output = HumanMessage("@12345:\nTest message")
        self.assertEqual(self.__mapper.map_to_langchain(author, message), expected_output)

    def test_map_to_langchain_with_ai_author(self):
        ai_author = User(
            id = UUID(int = 2),
            created_at = date.today(),
            telegram_username = TELEGRAM_BOT_USER.telegram_username,
            telegram_user_id = TELEGRAM_BOT_USER.telegram_user_id,
            full_name = TELEGRAM_BOT_USER.full_name,
        )
        message = ChatMessage(chat_id = "c2", message_id = "m2", text = "I'm an AI assistant.")
        expected_output = AIMessage("I'm an AI assistant.")
        self.assertEqual(self.__mapper.map_to_langchain(ai_author, message), expected_output)

    def test_map_to_langchain_no_author(self):
        message = ChatMessage(chat_id = "c1", message_id = "m1", text = "Test message")
        expected_output = AIMessage("Test message")
        self.assertEqual(self.__mapper.map_to_langchain(None, message), expected_output)

    def test_map_bot_message_to_storage_single_message(self):
        message = AIMessage(content = "Test message")
        chat_id = "test_chat"
        result = self.__mapper.map_bot_message_to_storage(chat_id, message)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].text, "Test message")
        self.assertEqual(result[0].chat_id, chat_id)
        self.assertEqual(result[0].author_id, TELEGRAM_BOT_USER.id)

    def test_map_bot_message_to_storage_multiple_messages(self):
        message = AIMessage(content = f"Message 1{MULTI_MESSAGE_DELIMITER}Message 2{MULTI_MESSAGE_DELIMITER}Message 3")
        chat_id = "test_chat"
        result = self.__mapper.map_bot_message_to_storage(chat_id, message)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].text, "Message 1")
        self.assertEqual(result[1].text, "Message 2")
        self.assertEqual(result[2].text, "Message 3")
        for message in result:
            self.assertEqual(message.chat_id, chat_id)
            self.assertEqual(message.author_id, TELEGRAM_BOT_USER.id)

    def test_map_bot_message_to_storage_empty_message(self):
        message = AIMessage(content = "")
        chat_id = "test_chat"
        result = self.__mapper.map_bot_message_to_storage(chat_id, message)
        self.assertEqual(len(result), 0)

    def test_map_bot_message_to_storage_list_of_strings(self):
        message = AIMessage(content = ["Message 1", "Message 2", "Message 3"])
        chat_id = "test_chat"
        result = self.__mapper.map_bot_message_to_storage(chat_id, message)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].text, "Message 1")
        self.assertEqual(result[1].text, "Message 2")
        self.assertEqual(result[2].text, "Message 3")
        for message in result:
            self.assertEqual(message.chat_id, chat_id)
            self.assertEqual(message.author_id, TELEGRAM_BOT_USER.id)

    def test_map_bot_message_to_storage_list_of_dicts(self):
        message = AIMessage(content = [{"name": "Mike", "city": "Valencia"}, {"name": "Dirk"}])
        chat_id = "test_chat"
        result = self.__mapper.map_bot_message_to_storage(chat_id, message)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].text, "name: Mike\ncity: Valencia")
        self.assertEqual(result[1].text, "name: Dirk")
        for message in result:
            self.assertEqual(message.chat_id, chat_id)
            self.assertEqual(message.author_id, TELEGRAM_BOT_USER.id)

    def test_map_bot_message_to_storage_message_id_uniqueness(self):
        message = AIMessage(content = "Test message")
        chat_id = "test_chat"
        result1 = self.__mapper.map_bot_message_to_storage(chat_id, message)
        result2 = self.__mapper.map_bot_message_to_storage(chat_id, message)
        self.assertNotEqual(result1[0].message_id, result2[0].message_id)
