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
from di.di import DI
from features.external_tools.access_token_resolver import AccessTokenResolver, TokenResolutionError
from features.external_tools.external_tool import ExternalTool, ExternalToolProvider, ToolType
from features.external_tools.external_tool_provider_library import (
    ANTHROPIC,
    COINMARKETCAP,
    GOOGLE_AI,
    OPEN_AI,
    PERPLEXITY,
    RAPID_API,
    REPLICATE,
)


class AccessTokenResolverTest(unittest.TestCase):
    invoker_user: User
    sponsor_user: User
    sponsorship: Sponsorship
    mock_user_dao: UserCRUD
    mock_sponsorship_dao: SponsorshipCRUD
    mock_di: DI
    openai_provider: ExternalToolProvider
    anthropic_provider: ExternalToolProvider
    openai_tool: ExternalTool

    def setUp(self):
        self.invoker_user = User(
            id = UUID(int = 1),
            full_name = "Invoker User",
            telegram_username = "invoker_user",
            telegram_chat_id = "invoker_chat_id",
            telegram_user_id = 1,
            open_ai_key = SecretStr("invoker_openai_key"),
            anthropic_key = SecretStr("invoker_anthropic_key"),
            google_ai_key = SecretStr("invoker_google_ai_key"),
            perplexity_key = SecretStr("invoker_perplexity_key"),
            replicate_key = SecretStr("invoker_replicate_key"),
            rapid_api_key = SecretStr("invoker_rapid_api_key"),
            coinmarketcap_key = SecretStr("invoker_coinmarketcap_key"),
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.sponsor_user = User(
            id = UUID(int = 2),
            full_name = "Sponsor User",
            telegram_username = "sponsor_user",
            telegram_chat_id = "sponsor_chat_id",
            telegram_user_id = 2,
            open_ai_key = SecretStr("sponsor_openai_key"),
            anthropic_key = SecretStr("sponsor_anthropic_key"),
            google_ai_key = SecretStr("sponsor_google_ai_key"),
            perplexity_key = SecretStr("sponsor_perplexity_key"),
            replicate_key = SecretStr("sponsor_replicate_key"),
            rapid_api_key = SecretStr("sponsor_rapid_api_key"),
            coinmarketcap_key = SecretStr("sponsor_coinmarketcap_key"),
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
        self.mock_di = Mock(spec = DI)
        # noinspection PyPropertyAccess
        self.mock_di.user_crud = self.mock_user_dao
        # noinspection PyPropertyAccess
        self.mock_di.sponsorship_crud = self.mock_sponsorship_dao
        # noinspection PyPropertyAccess
        self.mock_di.invoker = self.invoker_user

        self.openai_provider = OPEN_AI
        self.anthropic_provider = ANTHROPIC
        self.openai_tool = ExternalTool(
            id = "test-gpt-4",
            name = "Test GPT-4",
            provider = self.openai_provider,
            types = [ToolType.chat],
        )

    def test_init_with_user_object_success(self):
        resolver = AccessTokenResolver(self.mock_di)

        # Should not raise an exception
        self.assertIsNotNone(resolver)
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.get.assert_not_called()

    def test_get_access_token_success_user_has_direct_token(self):
        # Mock to avoid sponsorship lookup since user has direct token
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        resolver = AccessTokenResolver(self.mock_di)

        token = resolver.get_access_token(self.openai_provider)

        assert token is not None
        self.assertIsInstance(token, SecretStr)
        self.assertEqual(token.get_secret_value(), self.invoker_user.open_ai_key.get_secret_value())
        # noinspection PyUnresolvedReferences
        self.mock_sponsorship_dao.get_all_by_receiver.assert_not_called()

    def test_get_access_token_success_user_no_token_has_sponsorship(self):
        user_without_token = self.invoker_user.model_copy(update = {"open_ai_key": None})
        sponsorship_db = SponsorshipDB(**self.sponsorship.model_dump())
        sponsor_user_db = UserDB(**self.sponsor_user.model_dump())
        # noinspection PyPropertyAccess
        self.mock_di.invoker = user_without_token

        self.mock_sponsorship_dao.get_all_by_receiver.return_value = [sponsorship_db]
        self.mock_user_dao.get.return_value = sponsor_user_db

        resolver = AccessTokenResolver(self.mock_di)

        token = resolver.get_access_token(self.openai_provider)

        assert token is not None
        self.assertIsInstance(token, SecretStr)
        self.assertEqual(token.get_secret_value(), self.sponsor_user.open_ai_key.get_secret_value())
        # noinspection PyUnresolvedReferences
        self.mock_sponsorship_dao.get_all_by_receiver.assert_called_once_with(user_without_token.id, limit = 1)
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.get.assert_called_once_with(self.sponsorship.sponsor_id)

    def test_get_access_token_failure_user_no_token_no_sponsorship(self):
        user_without_token = self.invoker_user.model_copy(update = {"open_ai_key": None})
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []
        # noinspection PyPropertyAccess
        self.mock_di.invoker = user_without_token

        resolver = AccessTokenResolver(self.mock_di)

        token = resolver.get_access_token(self.openai_provider)

        assert token is None
        # noinspection PyUnresolvedReferences
        self.mock_sponsorship_dao.get_all_by_receiver.assert_called_once_with(user_without_token.id, limit = 1)

    def test_get_access_token_failure_user_no_token_sponsor_not_found(self):
        user_without_token = self.invoker_user.model_copy(update = {"open_ai_key": None})
        sponsorship_db = SponsorshipDB(**self.sponsorship.model_dump())
        # noinspection PyPropertyAccess
        self.mock_di.invoker = user_without_token

        self.mock_sponsorship_dao.get_all_by_receiver.return_value = [sponsorship_db]
        self.mock_user_dao.get.return_value = None

        resolver = AccessTokenResolver(self.mock_di)

        token = resolver.get_access_token(self.openai_provider)

        assert token is None
        # noinspection PyUnresolvedReferences
        self.mock_sponsorship_dao.get_all_by_receiver.assert_called_once_with(user_without_token.id, limit = 1)
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.get.assert_called_once_with(self.sponsorship.sponsor_id)

    def test_get_access_token_failure_user_no_token_sponsor_no_token(self):
        user_without_token = self.invoker_user.model_copy(update = {"open_ai_key": None})
        sponsor_without_token = self.sponsor_user.model_copy(update = {"open_ai_key": None})
        sponsorship_db = SponsorshipDB(**self.sponsorship.model_dump())
        sponsor_user_db = UserDB(**sponsor_without_token.model_dump())
        # noinspection PyPropertyAccess
        self.mock_di.invoker = user_without_token

        self.mock_sponsorship_dao.get_all_by_receiver.return_value = [sponsorship_db]
        self.mock_user_dao.get.return_value = sponsor_user_db

        resolver = AccessTokenResolver(self.mock_di)

        token = resolver.get_access_token(self.openai_provider)

        assert token is None

    def test_get_access_token_failure_unsupported_provider(self):
        # Set up mock to return empty list to avoid sponsorship lookup since user has direct token
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        # Create a truly unsupported provider
        unsupported_provider = ExternalToolProvider(
            id = "unsupported",
            name = "Unsupported Provider",
            token_management_url = "https://example.com",
            token_format = "test-token",
            tools = ["test-tool"],
        )

        resolver = AccessTokenResolver(self.mock_di)

        token = resolver.get_access_token(unsupported_provider)

        self.assertIsNone(token)

    def test_get_access_token_for_tool_success(self):
        # Mock to avoid sponsorship lookup since user has direct token
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        resolver = AccessTokenResolver(self.mock_di)

        token = resolver.get_access_token_for_tool(self.openai_tool)

        assert token is not None
        self.assertIsInstance(token, SecretStr)
        self.assertEqual(token.get_secret_value(), self.invoker_user.open_ai_key.get_secret_value())

    def test_require_access_token_success(self):
        # Mock to avoid sponsorship lookup since user has direct token
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        resolver = AccessTokenResolver(self.mock_di)

        token = resolver.require_access_token(self.openai_provider)

        assert token is not None
        self.assertIsInstance(token, SecretStr)
        self.assertEqual(token.get_secret_value(), self.invoker_user.open_ai_key.get_secret_value())

    def test_require_access_token_failure_raises_exception(self):
        user_without_token = self.invoker_user.model_copy(update = {"open_ai_key": None})
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []
        # noinspection PyPropertyAccess
        self.mock_di.invoker = user_without_token

        resolver = AccessTokenResolver(self.mock_di)

        with self.assertRaises(TokenResolutionError) as context:
            resolver.require_access_token(self.openai_provider)

        self.assertIn(f"Unable to resolve an access token for '{self.openai_provider.name}'", str(context.exception))

    def test_require_access_token_for_tool_success(self):
        # Mock to avoid sponsorship lookup since user has direct token
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        resolver = AccessTokenResolver(self.mock_di)

        token = resolver.require_access_token_for_tool(self.openai_tool)

        assert token is not None
        self.assertIsInstance(token, SecretStr)
        self.assertEqual(token.get_secret_value(), self.invoker_user.open_ai_key.get_secret_value())

    def test_require_access_token_for_tool_failure_raises_exception(self):
        user_without_token = self.invoker_user.model_copy(update = {"open_ai_key": None})
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []
        # noinspection PyPropertyAccess
        self.mock_di.invoker = user_without_token

        resolver = AccessTokenResolver(self.mock_di)

        with self.assertRaises(TokenResolutionError):
            resolver.require_access_token_for_tool(self.openai_tool)

    def test_get_access_token_anthropic_success_user_has_direct_token(self):
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        resolver = AccessTokenResolver(self.mock_di)

        token = resolver.get_access_token(ANTHROPIC)

        assert token is not None
        self.assertIsInstance(token, SecretStr)
        self.assertEqual(token.get_secret_value(), self.invoker_user.anthropic_key.get_secret_value())

    def test_get_access_token_perplexity_success_user_has_direct_token(self):
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        resolver = AccessTokenResolver(self.mock_di)

        token = resolver.get_access_token(PERPLEXITY)

        assert token is not None
        self.assertIsInstance(token, SecretStr)
        self.assertEqual(token.get_secret_value(), self.invoker_user.perplexity_key.get_secret_value())

    def test_get_access_token_replicate_success_user_has_direct_token(self):
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        resolver = AccessTokenResolver(self.mock_di)

        token = resolver.get_access_token(REPLICATE)

        assert token is not None
        self.assertIsInstance(token, SecretStr)
        self.assertEqual(token.get_secret_value(), self.invoker_user.replicate_key.get_secret_value())

    def test_get_access_token_rapid_api_success_user_has_direct_token(self):
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        resolver = AccessTokenResolver(self.mock_di)

        token = resolver.get_access_token(RAPID_API)

        assert token is not None
        self.assertIsInstance(token, SecretStr)
        self.assertEqual(token.get_secret_value(), self.invoker_user.rapid_api_key.get_secret_value())

    def test_get_access_token_coinmarketcap_success_user_has_direct_token(self):
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        resolver = AccessTokenResolver(self.mock_di)

        token = resolver.get_access_token(COINMARKETCAP)

        assert token is not None
        self.assertIsInstance(token, SecretStr)
        self.assertEqual(token.get_secret_value(), self.invoker_user.coinmarketcap_key.get_secret_value())

    def test_get_access_token_google_ai_success_user_has_direct_token(self):
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        resolver = AccessTokenResolver(self.mock_di)

        token = resolver.get_access_token(GOOGLE_AI)

        assert token is not None
        self.assertIsInstance(token, SecretStr)
        self.assertEqual(token.get_secret_value(), self.invoker_user.google_ai_key.get_secret_value())
