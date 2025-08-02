import unittest
import unittest.mock
from datetime import datetime, timedelta
from unittest.mock import Mock
from uuid import UUID

from pydantic import SecretStr

from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.model.user import UserDB
from db.schema.sponsorship import Sponsorship
from db.schema.user import User
from di.di import DI
from features.sponsorships.sponsorship_service import SponsorshipService
from util.config import config


class SponsorshipServiceTest(unittest.TestCase):
    user: User
    mock_user_dao: UserCRUD
    mock_sponsorship_dao: SponsorshipCRUD
    mock_di: DI
    service: SponsorshipService

    def setUp(self):
        self.user = User(
            id = UUID(int = 1),
            full_name = "Test User",
            telegram_username = "test_username",
            telegram_chat_id = "test_chat_id",
            telegram_user_id = 1,
            open_ai_key = SecretStr("test_api_key"),
            anthropic_key = None,
            perplexity_key = None,
            replicate_key = None,
            rapid_api_key = None,
            coinmarketcap_key = None,
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.mock_user_dao = Mock(spec = UserCRUD)
        self.mock_sponsorship_dao = Mock(spec = SponsorshipCRUD)
        self.mock_di = Mock(spec = DI)
        # noinspection PyPropertyAccess
        self.mock_di.user_crud = self.mock_user_dao
        # noinspection PyPropertyAccess
        self.mock_di.sponsorship_crud = self.mock_sponsorship_dao
        self.service = SponsorshipService(self.mock_di)

    def test_accept_sponsorship_success(self):
        # Create user without API keys for this test
        user_without_keys = self.user.model_copy(
            update = {
                "open_ai_key": None,
                "anthropic_key": None,
                "perplexity_key": None,
                "replicate_key": None,
                "rapid_api_key": None,
                "coinmarketcap_key": None,
            },
        )

        mock_sponsorship = Mock(
            accepted_at = None,
            sponsor_id = self.user.id,
            receiver_id = user_without_keys.id,
            sponsored_at = datetime.now() - timedelta(days = 1),
        )
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = [mock_sponsorship]
        self.mock_sponsorship_dao.save.return_value = {
            "sponsor_id": mock_sponsorship.sponsor_id,
            "receiver_id": mock_sponsorship.receiver_id,
            "sponsored_at": mock_sponsorship.sponsored_at,
            "accepted_at": datetime.now(),
        }

        result = self.service.accept_sponsorship(user_without_keys)

        self.assertTrue(result)
        # noinspection PyUnresolvedReferences
        self.mock_sponsorship_dao.save.assert_called()

    def test_sponsor_user_success(self):
        sponsor_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        receiver_user = User(
            id = UUID(int = 2),
            full_name = "Receiver User",
            telegram_username = receiver_telegram_username,
            telegram_chat_id = "receiver_chat_id",
            telegram_user_id = 2,
            open_ai_key = None,
            anthropic_key = None,
            perplexity_key = None,
            replicate_key = None,
            rapid_api_key = None,
            coinmarketcap_key = None,
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        receiver_user_db = UserDB(**receiver_user.model_dump())

        self.mock_user_dao.get.return_value = self.user
        self.mock_sponsorship_dao.get_all_by_sponsor.return_value = []
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []  # Ensure sponsor has no received sponsorships
        self.mock_user_dao.get_by_telegram_username.return_value = None
        self.mock_user_dao.save.return_value = receiver_user_db
        self.mock_sponsorship_dao.save.return_value = {
            "sponsor_id": self.user.id,
            "receiver_id": receiver_user_db.id,
            "sponsored_at": datetime.now(),
            "accepted_at": None,
        }

        result, msg = self.service.sponsor_user(sponsor_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, SponsorshipService.Result.success)
        self.assertIn("Sponsorship sent", msg)
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.get.assert_called_once_with(UUID(hex = sponsor_user_id_hex))
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.save.assert_called()

    def test_sponsor_user_failure_sponsor_not_found(self):
        sponsor_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        self.mock_user_dao.get.return_value = None

        result, msg = self.service.sponsor_user(sponsor_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, SponsorshipService.Result.failure)
        self.assertIn("Sponsor '", msg)

    def test_sponsor_user_failure_sponsoring_self(self):
        sponsor_user_id_hex = self.user.id.hex
        receiver_telegram_username = "test_username"

        self.mock_user_dao.get.return_value = self.user

        result, msg = self.service.sponsor_user(sponsor_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, SponsorshipService.Result.failure)
        self.assertIn("cannot sponsor themselves", msg)

    def test_sponsor_user_failure_max_sponsorships_exceeded(self):
        sponsor_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        self.mock_user_dao.get.return_value = self.user
        self.mock_sponsorship_dao.get_all_by_sponsor.return_value = [Mock()] * (config.max_sponsorships_per_user + 1)
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        result, msg = self.service.sponsor_user(sponsor_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, SponsorshipService.Result.failure)
        self.assertIn("exceeded the maximum number of sponsorships", msg)

    def test_sponsor_user_success_developer_no_limit(self):
        sponsor_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        developer_user = self.user.model_copy(update = {"group": UserDB.Group.developer})
        self.mock_user_dao.get.return_value = developer_user
        self.mock_sponsorship_dao.get_all_by_sponsor.return_value = [Mock()] * (config.max_sponsorships_per_user + 1)
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []
        self.mock_user_dao.get_by_telegram_username.return_value = None

        # Create a real user for the new user
        new_user = UserDB(
            id = UUID(int = 2),
            full_name = "New User",
            telegram_username = receiver_telegram_username,
            telegram_chat_id = "new_chat_id",
            telegram_user_id = 2,
            open_ai_key = developer_user.open_ai_key,
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )

        self.mock_user_dao.save.return_value = new_user

        # Create a more specific mock for the new sponsorship
        mock_sponsorship: Sponsorship = Mock(spec = Sponsorship)
        mock_sponsorship.sponsor_id = developer_user.id
        mock_sponsorship.receiver_id = new_user.id
        mock_sponsorship.sponsored_at = datetime.now()
        mock_sponsorship.accepted_at = None

        self.mock_sponsorship_dao.save.return_value = mock_sponsorship

        result, msg = self.service.sponsor_user(sponsor_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, SponsorshipService.Result.success)
        self.assertIn("Sponsorship sent", msg)

    def test_sponsor_user_failure_no_api_key(self):
        sponsor_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        # Create sponsor without any API keys
        sponsor_without_keys = self.user.model_copy(
            update = {
                "open_ai_key": None,
                "anthropic_key": None,
                "perplexity_key": None,
                "replicate_key": None,
                "rapid_api_key": None,
                "coinmarketcap_key": None,
            },
        )

        self.mock_user_dao.get.return_value = sponsor_without_keys
        # Mock the sponsorship checks that come before API key validation
        self.mock_sponsorship_dao.get_all_by_sponsor.return_value = []
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        result, msg = self.service.sponsor_user(sponsor_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, SponsorshipService.Result.failure)
        self.assertIn("has no API keys configured", msg)

    def test_sponsor_user_failure_transitive_sponsorship(self):
        sponsor_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        self.mock_user_dao.get.return_value = self.user
        self.mock_sponsorship_dao.get_all_by_sponsor.return_value = []
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = [Mock()]

        result, msg = self.service.sponsor_user(sponsor_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, SponsorshipService.Result.failure)
        self.assertIn("can't sponsor others before having a personal API key", msg)

    def test_sponsor_user_failure_receiver_has_sponsorship(self):
        sponsor_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        receiver_user = Mock(
            spec = User,
            id = UUID(int = 2),
            open_ai_key = None,
            full_name = "Receiver User",
            telegram_username = receiver_telegram_username,
            telegram_chat_id = "receiver_chat_id",
            telegram_user_id = 2,
        )
        self.mock_user_dao.get.return_value = self.user
        self.mock_user_dao.get_by_telegram_username.return_value = receiver_user
        self.mock_sponsorship_dao.get_all_by_receiver.side_effect = [
            [],
            [Mock(spec = Sponsorship)],
        ]
        self.mock_sponsorship_dao.get_all_by_sponsor.return_value = []

        result, msg = self.service.sponsor_user(sponsor_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, SponsorshipService.Result.failure)
        self.assertIn("Receiver '@receiver_username' already has a sponsorship", msg)

    def test_sponsor_user_failure_receiver_has_api_key(self):
        sponsor_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        receiver_user = User(
            id = UUID(int = 2),
            full_name = "Receiver User",
            telegram_username = receiver_telegram_username,
            telegram_chat_id = "receiver_chat_id",
            telegram_user_id = 2,
            open_ai_key = SecretStr("receiver_api_key"),
            anthropic_key = None,
            perplexity_key = None,
            replicate_key = None,
            rapid_api_key = None,
            coinmarketcap_key = None,
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )

        self.mock_user_dao.get.return_value = self.user
        self.mock_sponsorship_dao.get_all_by_sponsor.return_value = []
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []  # No transitive sponsoring
        self.mock_user_dao.get_by_telegram_username.return_value = receiver_user

        result, msg = self.service.sponsor_user(sponsor_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, SponsorshipService.Result.failure)
        self.assertIn("already has API keys configured", msg)

    def test_unsponsor_user_success(self):
        sponsor_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        sponsor_user_db = UserDB(**self.user.model_dump())
        receiver_user = User(
            id = UUID(int = 2),
            full_name = "Receiver User",
            telegram_username = receiver_telegram_username,
            telegram_chat_id = "receiver_chat_id",
            telegram_user_id = 2,
            open_ai_key = SecretStr("test_api_key"),
            anthropic_key = None,
            perplexity_key = None,
            replicate_key = None,
            rapid_api_key = None,
            coinmarketcap_key = None,
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        receiver_user_db = UserDB(**receiver_user.model_dump())

        # Create a mock sponsorship
        sponsorship_db = Sponsorship(
            sponsor_id = sponsor_user_db.id,
            receiver_id = receiver_user_db.id,
            sponsored_at = datetime.now(),
            accepted_at = None,
        )

        self.mock_user_dao.get.side_effect = [sponsor_user_db, receiver_user_db]
        self.mock_user_dao.get_by_telegram_username.return_value = receiver_user_db
        self.mock_sponsorship_dao.get.return_value = Mock(**sponsorship_db.model_dump())

        result, msg = self.service.unsponsor_user(sponsor_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, SponsorshipService.Result.success)
        self.assertIn("Sponsorship revoked", msg)
        # noinspection PyUnresolvedReferences
        self.mock_sponsorship_dao.delete.assert_called_once_with(sponsor_user_db.id, receiver_user_db.id)
        # Token removal is no longer handled by SponsorshipService
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.save.assert_not_called()

    def test_unsponsor_user_failure_sponsor_not_found(self):
        sponsor_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        self.mock_user_dao.get.side_effect = [None, None]

        result, msg = self.service.unsponsor_user(sponsor_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, SponsorshipService.Result.failure)
        self.assertIn("Sponsor '", msg)

    def test_unsponsor_user_failure_no_sponsorship(self):
        sponsor_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        sponsor_user_db = UserDB(**self.user.model_dump())
        receiver_user = User(
            id = UUID(int = 2),
            full_name = "Receiver User",
            telegram_username = receiver_telegram_username,
            telegram_chat_id = "receiver_chat_id",
            telegram_user_id = 2,
            open_ai_key = None,
            anthropic_key = None,
            perplexity_key = None,
            replicate_key = None,
            rapid_api_key = None,
            coinmarketcap_key = None,
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        receiver_user_db = UserDB(**receiver_user.model_dump())

        self.mock_user_dao.get.side_effect = [sponsor_user_db, receiver_user_db]
        self.mock_user_dao.get_by_telegram_username.return_value = receiver_user_db
        self.mock_sponsorship_dao.get.return_value = None

        result, msg = self.service.unsponsor_user(sponsor_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, SponsorshipService.Result.failure)
        self.assertIn("has no sponsorship", msg)

    def test_accept_sponsorship_failure_no_sponsorship(self):
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        result = self.service.accept_sponsorship(self.user)

        self.assertFalse(result)

    def test_accept_sponsorship_failure_has_api_key(self):
        # User with API keys cannot accept sponsorship
        user_with_keys = self.user  # This user already has open_ai_key set in setUp

        result = self.service.accept_sponsorship(user_with_keys)

        self.assertFalse(result)

    def test_accept_sponsorship_success_no_api_key(self):
        # User without API keys can accept sponsorship
        user_without_keys = self.user.model_copy(
            update = {
                "open_ai_key": None,
                "anthropic_key": None,
                "perplexity_key": None,
                "replicate_key": None,
                "rapid_api_key": None,
                "coinmarketcap_key": None,
            },
        )

        # Create a real pending sponsorship
        pending_sponsorship = Sponsorship(
            sponsor_id = UUID(int = 999),
            receiver_id = user_without_keys.id,
            sponsored_at = datetime.now(),
            accepted_at = None,
        )
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = [pending_sponsorship]
        self.mock_sponsorship_dao.save.return_value = pending_sponsorship

        result = self.service.accept_sponsorship(user_without_keys)

        self.assertTrue(result)

    def test_unsponsor_self_success(self):
        user_id_hex = self.user.id.hex
        sponsor_user = User(
            id = UUID(int = 2),
            full_name = "Sponsor User",
            telegram_username = "sponsor_username",
            telegram_chat_id = "sponsor_chat_id",
            telegram_user_id = 2,
            open_ai_key = SecretStr("sponsor_api_key"),
            anthropic_key = None,
            perplexity_key = None,
            replicate_key = None,
            rapid_api_key = None,
            coinmarketcap_key = None,
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        sponsor_user_db = UserDB(**sponsor_user.model_dump())
        user_db = UserDB(**self.user.model_dump())

        # Create a mock sponsorship where user is the receiver
        sponsorship_db = Mock(
            sponsor_id = sponsor_user.id,
            receiver_id = self.user.id,
            sponsored_at = datetime.now(),
            accepted_at = datetime.now(),
        )

        # user lookup, then unsponsor_user lookups
        self.mock_user_dao.get.side_effect = [
            user_db,
            sponsor_user_db,
            user_db,
        ]
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = [sponsorship_db]
        self.mock_user_dao.get_by_telegram_username.return_value = user_db
        self.mock_sponsorship_dao.get.return_value = sponsorship_db

        result, msg = self.service.unsponsor_self(user_id_hex)

        self.assertEqual(result, SponsorshipService.Result.success)
        self.assertIn("Sponsorship revoked", msg)
        # noinspection PyUnresolvedReferences
        self.mock_sponsorship_dao.delete.assert_called_once_with(sponsor_user.id, self.user.id)

    def test_unsponsor_self_failure_user_not_found(self):
        user_id_hex = self.user.id.hex

        self.mock_user_dao.get.return_value = None

        result, msg = self.service.unsponsor_self(user_id_hex)

        self.assertEqual(result, SponsorshipService.Result.failure)
        self.assertIn("User '", msg)
        self.assertIn("not found", msg)

    def test_unsponsor_self_failure_no_sponsorships(self):
        user_id_hex = self.user.id.hex
        user_db = UserDB(**self.user.model_dump())

        self.mock_user_dao.get.return_value = user_db
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        result, msg = self.service.unsponsor_self(user_id_hex)

        self.assertEqual(result, SponsorshipService.Result.failure)
        self.assertIn("has no sponsorships to remove", msg)

    def test_unsponsor_self_failure_no_telegram_username(self):
        user_id_hex = self.user.id.hex
        user_without_username = self.user.model_copy(update = {"telegram_username": None})
        user_db = UserDB(**user_without_username.model_dump())

        # Create a mock sponsorship
        sponsorship_db = Mock(
            sponsor_id = UUID(int = 2),
            receiver_id = self.user.id,
            sponsored_at = datetime.now(),
            accepted_at = datetime.now(),
        )

        self.mock_user_dao.get.return_value = user_db
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = [sponsorship_db]

        result, msg = self.service.unsponsor_self(user_id_hex)

        self.assertEqual(result, SponsorshipService.Result.failure)
        self.assertIn("has no telegram username", msg)

    def test_unsponsor_self_calls_unsponsor_user(self):
        user_id_hex = self.user.id.hex
        sponsor_user = User(
            id = UUID(int = 2),
            full_name = "Sponsor User",
            telegram_username = "sponsor_username",
            telegram_chat_id = "sponsor_chat_id",
            telegram_user_id = 2,
            open_ai_key = SecretStr("sponsor_api_key"),
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        sponsor_user_db = UserDB(**sponsor_user.model_dump())
        user_db = UserDB(**self.user.model_dump())

        # Create a mock sponsorship
        sponsorship_db = Mock(
            sponsor_id = sponsor_user.id,
            receiver_id = self.user.id,
            sponsored_at = datetime.now(),
            accepted_at = datetime.now(),
        )

        self.mock_user_dao.get.side_effect = [user_db, sponsor_user_db, user_db]
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = [sponsorship_db]
        self.mock_user_dao.get_by_telegram_username.return_value = user_db
        self.mock_sponsorship_dao.get.return_value = sponsorship_db

        # Mock the unsponsor_user method to verify it's called correctly
        with unittest.mock.patch.object(self.service, "unsponsor_user") as mock_unsponsor:
            mock_unsponsor.return_value = (SponsorshipService.Result.success, "Test message")

            result, msg = self.service.unsponsor_self(user_id_hex)

            mock_unsponsor.assert_called_once_with(sponsor_user.id.hex, self.user.telegram_username)
            self.assertEqual(result, SponsorshipService.Result.success)

    def test_user_has_any_api_key(self):
        # Test user with API key
        user_with_key = self.user  # Has open_ai_key from setUp
        self.assertTrue(user_with_key.has_any_api_key())

        # Test user without any API keys
        user_without_keys = self.user.model_copy(
            update = {
                "open_ai_key": None,
                "anthropic_key": None,
                "perplexity_key": None,
                "replicate_key": None,
                "rapid_api_key": None,
                "coinmarketcap_key": None,
            },
        )
        self.assertFalse(user_without_keys.has_any_api_key())

        # Test user with only anthropic key
        user_with_anthropic = user_without_keys.model_copy(update = {"anthropic_key": "test_anthropic_key"})
        self.assertTrue(user_with_anthropic.has_any_api_key())
