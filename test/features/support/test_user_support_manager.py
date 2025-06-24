import unittest
from datetime import datetime
from unittest.mock import Mock, patch
from uuid import UUID

from langchain_core.messages import AIMessage

from db.crud.user import UserCRUD
from db.model.user import UserDB
from db.schema.user import User
from features.support.user_support_manager import UserSupportManager


class UserSupportManagerTest(unittest.TestCase):
    user: User
    mock_user_dao: UserCRUD
    manager: UserSupportManager

    def setUp(self):
        self.user = User(
            id = UUID(int = 1),
            full_name = "Test User",
            telegram_username = "test_username",
            telegram_chat_id = "test_chat_id",
            telegram_user_id = 1,
            open_ai_key = "test_api_key",
            anthropic_key = "test_anthropic_key",
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.mock_user_dao = Mock()
        self.mock_user_dao.get.return_value = UserDB(**self.user.model_dump())
        self.mock_sponsorship_dao = Mock()
        self.manager = UserSupportManager(
            user_input = "Test input",
            invoker_user_id_hex = self.user.id.hex,
            invoker_github_username = "test_github",
            include_telegram_username = True,
            include_full_name = True,
            request_type_str = "bug",
            user_dao = self.mock_user_dao,
            sponsorship_dao = self.mock_sponsorship_dao,
        )

    def test_resolve_request_type(self):
        self.assertEqual(self.manager.request_type, UserSupportManager.RequestType.bug)

        manager = UserSupportManager(
            user_input = "Test input",
            invoker_user_id_hex = self.user.id.hex,
            invoker_github_username = "test_github",
            include_telegram_username = True,
            include_full_name = True,
            request_type_str = "invalid_type",
            user_dao = self.mock_user_dao,
            sponsorship_dao = self.mock_sponsorship_dao,
        )
        self.assertEqual(manager.request_type, UserSupportManager.RequestType.request)

    def test_validate_invoker_success(self):
        self.mock_user_dao.get.return_value = self.user
        # noinspection PyUnresolvedReferences
        self.manager._UserSupportManager__validate_invoker()
        self.assertEqual(self.manager.invoker, self.user)

    def test_validate_invoker_failure(self):
        self.mock_user_dao.get.return_value = None
        with self.assertRaises(ValueError):
            # noinspection PyUnresolvedReferences
            self.manager._UserSupportManager__validate_invoker()

    @patch("builtins.open", new_callable = unittest.mock.mock_open, read_data = "test template")
    def test_load_template(self, mock_open):
        # noinspection PyUnresolvedReferences
        template = self.manager._UserSupportManager__load_template()
        self.assertEqual(template, "test template")
        mock_open.assert_called_once()

    @patch("features.support.user_support_manager.UserSupportManager._UserSupportManager__load_template")
    @patch("features.prompting.prompt_library.support_request_generator")
    def test_generate_issue_description(self, mock_prompt_generator, mock_load_template):
        mock_load_template.return_value = "test template"
        mock_prompt_generator.return_value = "test prompt"

        with patch.object(self.manager, "_UserSupportManager__copywriter") as mock_llm:
            mock_llm.invoke.return_value = AIMessage("Generated description")
            # noinspection PyUnresolvedReferences
            description = self.manager._UserSupportManager__generate_issue_description()

        self.assertEqual(description, "Generated description")
        mock_load_template.assert_called_once()
        mock_prompt_generator.assert_called_once()
        mock_llm.invoke.assert_called_once()

    @patch("features.prompting.prompt_library")
    def test_generate_issue_title(self, mock_prompt_library):
        mock_prompt_library.support_request_title_generator = "test prompt"

        with patch.object(self.manager, "_UserSupportManager__copywriter") as mock_llm:
            mock_llm.invoke.return_value = AIMessage("Generated title")
            # noinspection PyUnresolvedReferences
            title = self.manager._UserSupportManager__generate_issue_title("Test description")

        self.assertEqual(title, "Generated title")
        mock_llm.invoke.assert_called_once()

    @patch("features.support.user_support_manager.UserSupportManager._UserSupportManager__generate_issue_description")
    @patch("features.support.user_support_manager.UserSupportManager._UserSupportManager__generate_issue_title")
    @patch("requests.post")
    def test_execute_success(self, mock_post, mock_generate_title, mock_generate_description):
        mock_generate_description.return_value = "Test description"
        mock_generate_title.return_value = "Test title"
        mock_post.return_value.json.return_value = {"html_url": "https://example.com/issue/1"}
        mock_post.return_value.raise_for_status = Mock()

        result = self.manager.execute()

        self.assertEqual(result, "https://example.com/issue/1")
        mock_generate_description.assert_called_once()
        mock_generate_title.assert_called_once()
        mock_post.assert_called_once()

    @patch("features.support.user_support_manager.UserSupportManager._UserSupportManager__generate_issue_description")
    @patch("features.support.user_support_manager.UserSupportManager._UserSupportManager__generate_issue_title")
    @patch("requests.post")
    def test_execute_failure(self, mock_post, mock_generate_title, mock_generate_description):
        mock_generate_description.return_value = "Test description"
        mock_generate_title.return_value = "Test title"
        mock_post.return_value.raise_for_status.side_effect = Exception("API Error")

        with self.assertRaises(Exception):
            self.manager.execute()

        mock_generate_description.assert_called_once()
        mock_generate_title.assert_called_once()
        mock_post.assert_called_once()
