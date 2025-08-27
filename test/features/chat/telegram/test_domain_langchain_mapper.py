import unittest
from datetime import date
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage

from db.model.chat_config import ChatConfigDB
from db.schema.chat_message import ChatMessage
from db.schema.user import User, UserSave
from features.chat.telegram.domain_langchain_mapper import DomainLangchainMapper
from features.integrations.integrations import resolve_agent_user
from features.prompting.prompt_library import CHAT_MESSAGE_DELIMITER


class DomainLangchainMapperTest(unittest.TestCase):

    agent_user: UserSave
    mapper: DomainLangchainMapper

    def setUp(self):
        self.agent_user = resolve_agent_user(ChatConfigDB.ChatType.telegram)
        self.mapper = DomainLangchainMapper()

    def test_map_to_langchain_with_author(self):
        author = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_user_id = 12345,
            telegram_username = "john_doe",
            full_name = "John Doe",
        )
        message = ChatMessage(chat_id = UUID(int = 1), message_id = "m1", text = "Hello, how are you?")
        expected_output = HumanMessage("@john_doe [John Doe]:\nHello, how are you?")
        self.assertEqual(self.mapper.map_to_langchain(author, message), expected_output)

    def test_map_to_langchain_with_slim_author(self):
        author = User(id = UUID(int = 1), created_at = date.today(), telegram_user_id = 12345)
        message = ChatMessage(chat_id = UUID(int = 1), message_id = "m1", text = "Test message")
        expected_output = HumanMessage("@12345:\nTest message")
        self.assertEqual(self.mapper.map_to_langchain(author, message), expected_output)

    def test_map_to_langchain_with_ai_author(self):
        ai_author = User(
            id = UUID(int = 2),
            created_at = date.today(),
            telegram_username = self.agent_user.telegram_username,
            telegram_user_id = self.agent_user.telegram_user_id,
            full_name = self.agent_user.full_name,
        )
        message = ChatMessage(chat_id = UUID(int = 2), message_id = "m2", text = "I'm an AI assistant.")
        expected_output = AIMessage("I'm an AI assistant.")
        self.assertEqual(self.mapper.map_to_langchain(ai_author, message), expected_output)

    def test_map_to_langchain_no_author(self):
        message = ChatMessage(chat_id = UUID(int = 1), message_id = "m1", text = "Test message")
        expected_output = AIMessage("Test message")
        self.assertEqual(self.mapper.map_to_langchain(None, message), expected_output)

    def test_map_bot_message_to_storage_single_message(self):
        message = AIMessage(content = "Test message")
        chat_id = UUID(int = 3)
        result = self.mapper.map_bot_message_to_storage(chat_id, message)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].text, "Test message")
        self.assertEqual(result[0].chat_id, chat_id)
        self.assertEqual(result[0].author_id, self.agent_user.id)

    def test_map_bot_message_to_storage_multiple_messages(self):
        message = AIMessage(content = f"Message 1{CHAT_MESSAGE_DELIMITER}Message 2{CHAT_MESSAGE_DELIMITER}Message 3")
        chat_id = UUID(int = 3)
        result = self.mapper.map_bot_message_to_storage(chat_id, message)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].text, "Message 1")
        self.assertEqual(result[1].text, "Message 2")
        self.assertEqual(result[2].text, "Message 3")
        for message in result:
            self.assertEqual(message.chat_id, chat_id)
            self.assertEqual(message.author_id, self.agent_user.id)

    def test_map_bot_message_to_storage_empty_message(self):
        message = AIMessage(content = "")
        chat_id = UUID(int = 3)
        result = self.mapper.map_bot_message_to_storage(chat_id, message)
        self.assertEqual(len(result), 0)

    def test_map_bot_message_to_storage_list_of_strings(self):
        message = AIMessage(content = ["Message 1", "Message 2", "Message 3"])
        chat_id = UUID(int = 3)
        result = self.mapper.map_bot_message_to_storage(chat_id, message)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].text, "Message 1")
        self.assertEqual(result[1].text, "Message 2")
        self.assertEqual(result[2].text, "Message 3")
        for message in result:
            self.assertEqual(message.chat_id, chat_id)
            self.assertEqual(message.author_id, self.agent_user.id)

    def test_map_bot_message_to_storage_list_of_dicts(self):
        message = AIMessage(content = [{"name": "Mike", "city": "Valencia"}, {"name": "Dirk"}])
        chat_id = UUID(int = 3)
        result = self.mapper.map_bot_message_to_storage(chat_id, message)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].text, "name: Mike\ncity: Valencia")
        self.assertEqual(result[1].text, "name: Dirk")
        for message in result:
            self.assertEqual(message.chat_id, chat_id)
            self.assertEqual(message.author_id, self.agent_user.id)

    def test_map_bot_message_to_storage_message_id_uniqueness(self):
        message = AIMessage(content = "Test message")
        chat_id = UUID(int = 3)
        result1 = self.mapper.map_bot_message_to_storage(chat_id, message)
        result2 = self.mapper.map_bot_message_to_storage(chat_id, message)
        self.assertNotEqual(result1[0].message_id, result2[0].message_id)
