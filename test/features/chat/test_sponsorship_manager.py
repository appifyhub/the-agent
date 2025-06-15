import unittest
import unittest.mock
from datetime import datetime, timedelta
from unittest.mock import Mock
from uuid import UUID

from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.model.user import UserDB
from db.schema.sponsorship import Sponsorship
from db.schema.user import User
from features.sponsorships.sponsorship_service import SponsorshipService
from util.config import config


class SponsorshipManagerTest(unittest.TestCase):
    user: User
    mock_user_dao: UserCRUD
    mock_sponsorship_dao: SponsorshipCRUD
    manager: SponsorshipService

    def setUp(self):
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
        self.mock_user_dao = Mock(spec = UserCRUD)
        self.mock_sponsorship_dao = Mock(spec = SponsorshipCRUD)
        self.manager = SponsorshipService(self.mock_user_dao, self.mock_sponsorship_dao)

    def test_accept_sponsorship_success(self):
        mock_sponsorship = Mock(
            accepted_at = None,
            sponsor_id = self.user.id,
            receiver_id = self.user.id,
            sponsored_at = datetime.now() - timedelta(days = 1),
        )
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = [mock_sponsorship]
        self.mock_sponsorship_dao.save.return_value = {
            "sponsor_id": mock_sponsorship.sponsor_id,
            "receiver_id": mock_sponsorship.receiver_id,
            "sponsored_at": mock_sponsorship.sponsored_at,
            "accepted_at": datetime.now(),
        }

        result = self.manager.accept_sponsorship(self.user)

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

        result, msg = self.manager.sponsor_user(sponsor_user_id_hex, receiver_telegram_username)

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

        result, msg = self.manager.sponsor_user(sponsor_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, SponsorshipService.Result.failure)
        self.assertIn("Sponsor '", msg)

    def test_sponsor_user_failure_sponsoring_self(self):
        sponsor_user_id_hex = self.user.id.hex
        receiver_telegram_username = "test_username"

        self.mock_user_dao.get.return_value = self.user

        result, msg = self.manager.sponsor_user(sponsor_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, SponsorshipService.Result.failure)
        self.assertIn("cannot sponsor themselves", msg)

    def test_sponsor_user_failure_max_sponsorships_exceeded(self):
        sponsor_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        self.mock_user_dao.get.return_value = self.user
        self.mock_sponsorship_dao.get_all_by_sponsor.return_value = [Mock()] * (config.max_sponsorships_per_user + 1)
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        result, msg = self.manager.sponsor_user(sponsor_user_id_hex, receiver_telegram_username)

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

        # Create a more specific mock for the new user
        mock_new_user = Mock(spec = UserDB)
        mock_new_user.id = UUID(int = 2)
        mock_new_user.full_name = "New User"
        mock_new_user.telegram_username = receiver_telegram_username
        mock_new_user.telegram_chat_id = "new_chat_id"
        mock_new_user.telegram_user_id = 2
        mock_new_user.open_ai_key = developer_user.open_ai_key
        mock_new_user.group = UserDB.Group.standard
        mock_new_user.created_at = datetime.now().date()

        self.mock_user_dao.save.return_value = mock_new_user

        # Create a more specific mock for the new sponsorship
        mock_sponsorship: Sponsorship = Mock(spec = Sponsorship)
        mock_sponsorship.sponsor_id = developer_user.id
        mock_sponsorship.receiver_id = mock_new_user.id
        mock_sponsorship.sponsored_at = datetime.now()
        mock_sponsorship.accepted_at = None

        self.mock_sponsorship_dao.save.return_value = mock_sponsorship

        result, msg = self.manager.sponsor_user(sponsor_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, SponsorshipService.Result.success)
        self.assertIn("Sponsorship sent", msg)

    def test_sponsor_user_failure_no_api_key(self):
        sponsor_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        user_without_key = self.user.model_copy(update = {"open_ai_key": None})
        self.mock_user_dao.get.return_value = user_without_key
        self.mock_sponsorship_dao.get_all_by_sponsor.return_value = []  # Mocking it as a list

        result, msg = self.manager.sponsor_user(sponsor_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, SponsorshipService.Result.failure)
        self.assertIn("has no valid API key", msg)

    def test_sponsor_user_failure_transitive_sponsorship(self):
        sponsor_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        self.mock_user_dao.get.return_value = self.user
        self.mock_sponsorship_dao.get_all_by_sponsor.return_value = []
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = [Mock()]

        result, msg = self.manager.sponsor_user(sponsor_user_id_hex, receiver_telegram_username)

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
            [], [Mock(spec = Sponsorship)],
        ]
        self.mock_sponsorship_dao.get_all_by_sponsor.return_value = []

        result, msg = self.manager.sponsor_user(sponsor_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, SponsorshipService.Result.failure)
        self.assertIn("Receiver '@receiver_username' already has a sponsorship", msg)

    def test_sponsor_user_failure_receiver_has_api_key(self):
        sponsor_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        receiver_user = Mock(spec = User, id = UUID(int = 2), open_ai_key = "receiver_api_key")
        self.mock_user_dao.get.return_value = self.user
        self.mock_sponsorship_dao.get_all_by_sponsor.return_value = []
        self.mock_user_dao.get_by_telegram_username.return_value = receiver_user
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        result, msg = self.manager.sponsor_user(sponsor_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, SponsorshipService.Result.failure)
        self.assertIn("already has an API key set up", msg)

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
            open_ai_key = "test_api_key",
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

        result, msg = self.manager.unsponsor_user(sponsor_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, SponsorshipService.Result.success)
        self.assertIn("Sponsorship revoked", msg)
        # noinspection PyUnresolvedReferences
        self.mock_sponsorship_dao.delete.assert_called_once_with(sponsor_user_db.id, receiver_user_db.id)
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.save.assert_called()

    def test_unsponsor_user_failure_sponsor_not_found(self):
        sponsor_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        self.mock_user_dao.get.side_effect = [None, None]

        result, msg = self.manager.unsponsor_user(sponsor_user_id_hex, receiver_telegram_username)

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
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        receiver_user_db = UserDB(**receiver_user.model_dump())

        self.mock_user_dao.get.side_effect = [sponsor_user_db, receiver_user_db]
        self.mock_user_dao.get_by_telegram_username.return_value = receiver_user_db
        self.mock_sponsorship_dao.get.return_value = None

        result, msg = self.manager.unsponsor_user(sponsor_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, SponsorshipService.Result.failure)
        self.assertIn("has no sponsorship", msg)

    def test_accept_sponsorship_failure_no_sponsorship(self):
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        result = self.manager.accept_sponsorship(self.user)

        self.assertFalse(result)

    def test_accept_sponsorship_failure_no_api_key(self):
        user_without_key = self.user.model_copy(update = {"open_ai_key": None})

        result = self.manager.accept_sponsorship(user_without_key)

        self.assertFalse(result)

    def test_unsponsor_self_success(self):
        user_id_hex = self.user.id.hex
        sponsor_user = User(
            id = UUID(int = 2),
            full_name = "Sponsor User",
            telegram_username = "sponsor_username",
            telegram_chat_id = "sponsor_chat_id",
            telegram_user_id = 2,
            open_ai_key = "sponsor_api_key",
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
            user_db, sponsor_user_db, user_db,
        ]
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = [sponsorship_db]
        self.mock_user_dao.get_by_telegram_username.return_value = user_db
        self.mock_sponsorship_dao.get.return_value = sponsorship_db

        result, msg = self.manager.unsponsor_self(user_id_hex)

        self.assertEqual(result, SponsorshipService.Result.success)
        self.assertIn("Sponsorship revoked", msg)
        # noinspection PyUnresolvedReferences
        self.mock_sponsorship_dao.delete.assert_called_once_with(sponsor_user.id, self.user.id)

    def test_unsponsor_self_failure_user_not_found(self):
        user_id_hex = self.user.id.hex

        self.mock_user_dao.get.return_value = None

        result, msg = self.manager.unsponsor_self(user_id_hex)

        self.assertEqual(result, SponsorshipService.Result.failure)
        self.assertIn("User '", msg)
        self.assertIn("not found", msg)

    def test_unsponsor_self_failure_no_sponsorships(self):
        user_id_hex = self.user.id.hex
        user_db = UserDB(**self.user.model_dump())

        self.mock_user_dao.get.return_value = user_db
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

        result, msg = self.manager.unsponsor_self(user_id_hex)

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

        result, msg = self.manager.unsponsor_self(user_id_hex)

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
            open_ai_key = "sponsor_api_key",
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
        with unittest.mock.patch.object(self.manager, "unsponsor_user") as mock_unsponsor:
            mock_unsponsor.return_value = (SponsorshipService.Result.success, "Test message")

            result, msg = self.manager.unsponsor_self(user_id_hex)

            mock_unsponsor.assert_called_once_with(sponsor_user.id.hex, self.user.telegram_username)
            self.assertEqual(result, SponsorshipService.Result.success)
