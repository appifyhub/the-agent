import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

from langchain_core.messages import AIMessage

from db.crud.user import UserCRUD
from db.model.user import UserDB
from db.schema.user import User
from features.web_browsing.ai_web_search import AIWebSearch
from util.config import config


class AIWebSearchTest(unittest.TestCase):
    user: User
    mock_user_crud: UserCRUD

    def setUp(self):
        config.web_timeout_s = 1
        self.user = User(
            id = UUID(int = 1),
            full_name = "Test User",
            telegram_username = "test_username",
            telegram_chat_id = "test_chat_id",
            telegram_user_id = 1,
            open_ai_key = "test_api_key",
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.mock_user_crud = MagicMock()
        self.mock_user_crud.get.return_value = self.user

    def test_init_valid_user(self):
        search = AIWebSearch(self.user.id.hex, "test query", self.mock_user_crud)
        self.assertIsInstance(search, AIWebSearch)

    def test_init_user_not_found(self):
        self.mock_user_crud.get.return_value = None
        with self.assertRaises(ValueError):
            AIWebSearch("non_existent_user_id", "test query", self.mock_user_crud)

    @patch("features.web_browsing.ai_web_search.ChatPerplexity")
    def test_execute_successful(self, mock_chat_perplexity):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "Test response")
        mock_chat_perplexity.return_value = mock_llm

        search = AIWebSearch(self.user.id.hex, "test query", self.mock_user_crud)
        result = search.execute()

        self.assertIsInstance(result, AIMessage)
        self.assertEqual(result.content, "Test response")

    @patch("features.web_browsing.ai_web_search.ChatPerplexity")
    def test_execute_non_ai_message_response(self, mock_chat_perplexity):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "Not an AIMessage"
        mock_chat_perplexity.return_value = mock_llm

        search = AIWebSearch(self.user.id.hex, "test query", self.mock_user_crud)
        with self.assertRaises(AssertionError):
            search.execute()

    @patch("features.web_browsing.ai_web_search.ChatPerplexity")
    def test_execute_exception_handling(self, mock_chat_perplexity):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("Test exception")
        mock_chat_perplexity.return_value = mock_llm

        search = AIWebSearch(self.user.id.hex, "test query", self.mock_user_crud)
        with self.assertRaises(Exception):
            search.execute()

    @patch("features.web_browsing.ai_web_search.ChatPerplexity")
    def test_execute_system_invocation(self, mock_chat_perplexity):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "System invocation response")
        mock_chat_perplexity.return_value = mock_llm

        search = AIWebSearch(None, "system query", self.mock_user_crud)
        result = search.execute()

        self.assertIsInstance(result, AIMessage)
        self.assertEqual(result.content, "System invocation response")
