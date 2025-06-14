import unittest
from datetime import datetime
from unittest.mock import Mock
from uuid import UUID

from pydantic import SecretStr

from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.model.sponsorship import SponsorshipDB
from db.model.user import UserDB
from db.schema.sponsorship import Sponsorship
from db.schema.user import User
from features.ai_tools.access_token_resolver import AccessTokenResolver, TokenResolutionError
from features.ai_tools.external_ai_tool import ExternalAiTool, ToolProvider, ToolType
from features.ai_tools.external_ai_tool_provider_library import ANTHROPIC, OPEN_AI


class AccessTokenResolverTest(unittest.TestCase):
    invoker_user: User
    sponsor_user: User
    sponsorship: Sponsorship
    mock_user_dao: Mock
    mock_sponsorship_dao: Mock
    openai_provider: ToolProvider
    anthropic_provider: ToolProvider
    openai_tool: ExternalAiTool

    def setUp(self):
        self.invoker_user = User(
            id = UUID(int = 1),
            full_name = "Invoker User",
            telegram_username = "invoker_user",
            telegram_chat_id = "invoker_chat_id",
            telegram_user_id = 1,
            open_ai_key = "invoker_openai_key",
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.sponsor_user = User(
            id = UUID(int = 2),
            full_name = "Sponsor User",
            telegram_username = "sponsor_user",
            telegram_chat_id = "sponsor_chat_id",
            telegram_user_id = 2,
            open_ai_key = "sponsor_openai_key",
            group = UserDB.Group.developer,
            created_at = datetime.now().date(),
        )
        self.sponsorship = Sponsorship(
            sponsor_id = self.sponsor_user.id,
            receiver_id = self.invoker_user.id,
            sponsored_at = datetime.now(),
            accepted_at = datetime.now(),
        )

        self.mock_user_dao = Mock(spec = UserCRUD)
        self.mock_sponsorship_dao = Mock(spec = SponsorshipCRUD)

        self.openai_provider = OPEN_AI
        self.anthropic_provider = ANTHROPIC
        self.openai_tool = ExternalAiTool(
            id = "test-gpt-4",
            name = "Test GPT-4",
            provider = self.openai_provider,
            types = [ToolType.llm],
        )

    def test_init_with_user_object_success(self):
        resolver = AccessTokenResolver(
            user_dao = self.mock_user_dao,
            sponsorship_dao = self.mock_sponsorship_dao,
            invoker_user = self.invoker_user,
        )

        # Should not raise an exception
        self.assertIsNotNone(resolver)
        self.mock_user_dao.get.assert_not_called()

    def test_init_with_user_id_hex_success(self):
        user_db = UserDB(**self.invoker_user.model_dump())
        self.mock_user_dao.get.return_value = user_db

        resolver = AccessTokenResolver(
            user_dao = self.mock_user_dao,
            sponsorship_dao = self.mock_sponsorship_dao,
            invoker_user_id_hex = self.invoker_user.id.hex,
        )

        self.assertIsNotNone(resolver)
        self.mock_user_dao.get.assert_called_once_with(self.invoker_user.id)

    def test_init_failure_no_parameters(self):
        with self.assertRaises(ValueError) as context:
            AccessTokenResolver(
                user_dao = self.mock_user_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
            )

        self.assertIn("Either invoker_user or invoker_user_id_hex must be provided", str(context.exception))

    def test_init_failure_user_not_found(self):
        self.mock_user_dao.get.return_value = None

        with self.assertRaises(ValueError) as context:
            AccessTokenResolver(
                user_dao = self.mock_user_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
                invoker_user_id_hex = self.invoker_user.id.hex,
            )

        self.assertIn(f"Invoker user '{self.invoker_user.id.hex}' not found", str(context.exception))

    def test_get_access_token_success_user_has_direct_token(self):
        # Mock to avoid sponsorship lookup since user has direct token
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        resolver = AccessTokenResolver(
            user_dao = self.mock_user_dao,
            sponsorship_dao = self.mock_sponsorship_dao,
            invoker_user = self.invoker_user,
        )

        token = resolver.get_access_token(self.openai_provider)

        self.assertIsNotNone(token)
        self.assertIsInstance(token, SecretStr)
        self.assertEqual(token.get_secret_value(), self.invoker_user.open_ai_key)
        self.mock_sponsorship_dao.get_all_by_receiver.assert_not_called()

    def test_get_access_token_success_user_no_token_has_sponsorship(self):
        user_without_token = self.invoker_user.model_copy(update = {"open_ai_key": None})
        sponsorship_db = SponsorshipDB(**self.sponsorship.model_dump())
        sponsor_user_db = UserDB(**self.sponsor_user.model_dump())

        self.mock_sponsorship_dao.get_all_by_receiver.return_value = [sponsorship_db]
        self.mock_user_dao.get.return_value = sponsor_user_db

        resolver = AccessTokenResolver(
            user_dao = self.mock_user_dao,
            sponsorship_dao = self.mock_sponsorship_dao,
            invoker_user = user_without_token,
        )

        token = resolver.get_access_token(self.openai_provider)

        self.assertIsNotNone(token)
        self.assertIsInstance(token, SecretStr)
        self.assertEqual(token.get_secret_value(), self.sponsor_user.open_ai_key)
        self.mock_sponsorship_dao.get_all_by_receiver.assert_called_once_with(user_without_token.id, limit = 1)
        self.mock_user_dao.get.assert_called_once_with(self.sponsorship.sponsor_id)

    def test_get_access_token_failure_user_no_token_no_sponsorship(self):
        user_without_token = self.invoker_user.model_copy(update = {"open_ai_key": None})
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        resolver = AccessTokenResolver(
            user_dao = self.mock_user_dao,
            sponsorship_dao = self.mock_sponsorship_dao,
            invoker_user = user_without_token,
        )

        token = resolver.get_access_token(self.openai_provider)

        self.assertIsNone(token)
        self.mock_sponsorship_dao.get_all_by_receiver.assert_called_once_with(user_without_token.id, limit = 1)

    def test_get_access_token_failure_user_no_token_sponsor_not_found(self):
        user_without_token = self.invoker_user.model_copy(update = {"open_ai_key": None})
        sponsorship_db = SponsorshipDB(**self.sponsorship.model_dump())

        self.mock_sponsorship_dao.get_all_by_receiver.return_value = [sponsorship_db]
        self.mock_user_dao.get.return_value = None

        resolver = AccessTokenResolver(
            user_dao = self.mock_user_dao,
            sponsorship_dao = self.mock_sponsorship_dao,
            invoker_user = user_without_token,
        )

        token = resolver.get_access_token(self.openai_provider)

        self.assertIsNone(token)
        self.mock_sponsorship_dao.get_all_by_receiver.assert_called_once_with(user_without_token.id, limit = 1)
        self.mock_user_dao.get.assert_called_once_with(self.sponsorship.sponsor_id)

    def test_get_access_token_failure_user_no_token_sponsor_no_token(self):
        user_without_token = self.invoker_user.model_copy(update = {"open_ai_key": None})
        sponsor_without_token = self.sponsor_user.model_copy(update = {"open_ai_key": None})
        sponsorship_db = SponsorshipDB(**self.sponsorship.model_dump())
        sponsor_user_db = UserDB(**sponsor_without_token.model_dump())

        self.mock_sponsorship_dao.get_all_by_receiver.return_value = [sponsorship_db]
        self.mock_user_dao.get.return_value = sponsor_user_db

        resolver = AccessTokenResolver(
            user_dao = self.mock_user_dao,
            sponsorship_dao = self.mock_sponsorship_dao,
            invoker_user = user_without_token,
        )

        token = resolver.get_access_token(self.openai_provider)

        self.assertIsNone(token)

    def test_get_access_token_failure_unsupported_provider(self):
        # Set up mock to return empty list to avoid sponsorship lookup since user has direct token
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        resolver = AccessTokenResolver(
            user_dao = self.mock_user_dao,
            sponsorship_dao = self.mock_sponsorship_dao,
            invoker_user = self.invoker_user,
        )

        token = resolver.get_access_token(self.anthropic_provider)

        self.assertIsNone(token)

    def test_get_access_token_for_tool_success(self):
        # Mock to avoid sponsorship lookup since user has direct token
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        resolver = AccessTokenResolver(
            user_dao = self.mock_user_dao,
            sponsorship_dao = self.mock_sponsorship_dao,
            invoker_user = self.invoker_user,
        )

        token = resolver.get_access_token_for_tool(self.openai_tool)

        self.assertIsNotNone(token)
        self.assertIsInstance(token, SecretStr)
        self.assertEqual(token.get_secret_value(), self.invoker_user.open_ai_key)

    def test_require_access_token_success(self):
        # Mock to avoid sponsorship lookup since user has direct token
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        resolver = AccessTokenResolver(
            user_dao = self.mock_user_dao,
            sponsorship_dao = self.mock_sponsorship_dao,
            invoker_user = self.invoker_user,
        )

        token = resolver.require_access_token(self.openai_provider)

        self.assertIsNotNone(token)
        self.assertIsInstance(token, SecretStr)
        self.assertEqual(token.get_secret_value(), self.invoker_user.open_ai_key)

    def test_require_access_token_failure_raises_exception(self):
        user_without_token = self.invoker_user.model_copy(update = {"open_ai_key": None})
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        resolver = AccessTokenResolver(
            user_dao = self.mock_user_dao,
            sponsorship_dao = self.mock_sponsorship_dao,
            invoker_user = user_without_token,
        )

        with self.assertRaises(TokenResolutionError) as context:
            resolver.require_access_token(self.openai_provider)

        self.assertIn(f"Unable to resolve an access token for '{self.openai_provider.name}'", str(context.exception))

    def test_require_access_token_for_tool_success(self):
        # Mock to avoid sponsorship lookup since user has direct token
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        resolver = AccessTokenResolver(
            user_dao = self.mock_user_dao,
            sponsorship_dao = self.mock_sponsorship_dao,
            invoker_user = self.invoker_user,
        )

        token = resolver.require_access_token_for_tool(self.openai_tool)

        self.assertIsNotNone(token)
        self.assertIsInstance(token, SecretStr)
        self.assertEqual(token.get_secret_value(), self.invoker_user.open_ai_key)

    def test_require_access_token_for_tool_failure_raises_exception(self):
        user_without_token = self.invoker_user.model_copy(update = {"open_ai_key": None})
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        resolver = AccessTokenResolver(
            user_dao = self.mock_user_dao,
            sponsorship_dao = self.mock_sponsorship_dao,
            invoker_user = user_without_token,
        )

        with self.assertRaises(TokenResolutionError) as context:
            resolver.require_access_token_for_tool(self.openai_tool)

        expected_message = f"Unable to resolve an access token for '{self.openai_provider.name}' - '{self.openai_tool.name}'"
        self.assertIn(expected_message, str(context.exception))
