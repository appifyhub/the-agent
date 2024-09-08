import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock
from uuid import UUID

from db.model.user import UserDB
from db.schema.invite import Invite
from db.schema.user import User
from features.chat.invite_manager import InviteManager
from util.config import config


class InviteManagerTest(unittest.TestCase):
    user: User
    mock_user_dao: Mock
    mock_invite_dao: Mock
    manager: InviteManager

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
        self.mock_user_dao = Mock()
        self.mock_invite_dao = Mock()
        self.manager = InviteManager(self.mock_user_dao, self.mock_invite_dao)

    def test_accept_invite_success(self):
        mock_invite = Mock(
            accepted_at = None,
            sender_id = self.user.id,
            receiver_id = self.user.id,
            invited_at = datetime.now() - timedelta(days = 1)
        )
        self.mock_invite_dao.get_all_by_receiver.return_value = [mock_invite]
        self.mock_invite_dao.save.return_value = {
            "sender_id": mock_invite.sender_id,
            "receiver_id": mock_invite.receiver_id,
            "invited_at": mock_invite.invited_at,
            "accepted_at": datetime.now()
        }

        result = self.manager.accept_invite(self.user)

        self.assertTrue(result)
        self.mock_invite_dao.save.assert_called()

    def test_invite_user_success(self):
        sender_user_id_hex = self.user.id.hex
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
        self.mock_invite_dao.get_all_by_sender.return_value = []
        self.mock_invite_dao.get_all_by_receiver.return_value = []  # Ensure sender has no received invites
        self.mock_user_dao.get_by_telegram_username.return_value = None
        self.mock_user_dao.save.return_value = receiver_user_db
        self.mock_invite_dao.save.return_value = {
            "sender_id": self.user.id,
            "receiver_id": receiver_user_db.id,
            "invited_at": datetime.now(),
            "accepted_at": None,
        }

        result, msg = self.manager.invite_user(sender_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, InviteManager.Result.success)
        self.assertIn("Invite sent", msg)
        self.mock_user_dao.get.assert_called_once_with(UUID(hex = sender_user_id_hex))
        self.mock_user_dao.save.assert_called()

    def test_invite_user_failure_sender_not_found(self):
        sender_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        self.mock_user_dao.get.return_value = None

        result, msg = self.manager.invite_user(sender_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, InviteManager.Result.failure)
        self.assertIn("Sender '", msg)

    def test_invite_user_failure_inviting_self(self):
        sender_user_id_hex = self.user.id.hex
        receiver_telegram_username = "test_username"

        self.mock_user_dao.get.return_value = self.user

        result, msg = self.manager.invite_user(sender_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, InviteManager.Result.failure)
        self.assertIn("cannot invite themselves", msg)

    def test_invite_user_failure_max_invites_exceeded(self):
        sender_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        self.mock_user_dao.get.return_value = self.user
        self.mock_invite_dao.get_all_by_sender.return_value = [Mock()] * (config.max_invites_per_user + 1)
        self.mock_invite_dao.get_all_by_receiver.return_value = []

        result, msg = self.manager.invite_user(sender_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, InviteManager.Result.failure)
        self.assertIn("exceeded the maximum number of invites", msg)

    def test_invite_user_success_developer_no_limit(self):
        sender_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        developer_user = self.user.model_copy(update = {"group": UserDB.Group.developer})
        self.mock_user_dao.get.return_value = developer_user
        self.mock_invite_dao.get_all_by_sender.return_value = [Mock()] * (config.max_invites_per_user + 1)
        self.mock_invite_dao.get_all_by_receiver.return_value = []
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

        # Create a more specific mock for the new invite
        mock_invite = Mock(spec = Invite)
        mock_invite.sender_id = developer_user.id
        mock_invite.receiver_id = mock_new_user.id
        mock_invite.invited_at = datetime.now()
        mock_invite.accepted_at = None

        self.mock_invite_dao.save.return_value = mock_invite

        result, msg = self.manager.invite_user(sender_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, InviteManager.Result.success)
        self.assertIn("Invite sent", msg)

    def test_invite_user_failure_no_api_key(self):
        sender_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        user_without_key = self.user.model_copy(update = {"open_ai_key": None})
        self.mock_user_dao.get.return_value = user_without_key
        self.mock_invite_dao.get_all_by_sender.return_value = []  # Mocking it as a list

        result, msg = self.manager.invite_user(sender_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, InviteManager.Result.failure)
        self.assertIn("has no valid API key", msg)

    def test_invite_user_failure_transitive_invite(self):
        sender_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        self.mock_user_dao.get.return_value = self.user
        self.mock_invite_dao.get_all_by_sender.return_value = []
        self.mock_invite_dao.get_all_by_receiver.return_value = [Mock()]

        result, msg = self.manager.invite_user(sender_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, InviteManager.Result.failure)
        self.assertIn("can't invite others until they start using their own API key", msg)

    def test_invite_user_failure_receiver_has_invite(self):
        sender_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        receiver_user = Mock(
            spec = User,
            id = UUID(int = 2),
            open_ai_key = None,
            full_name = 'Receiver User',
            telegram_username = receiver_telegram_username,
            telegram_chat_id = 'receiver_chat_id',
            telegram_user_id = 2,
        )
        self.mock_user_dao.get.return_value = self.user
        self.mock_user_dao.get_by_telegram_username.return_value = receiver_user
        self.mock_invite_dao.get_all_by_receiver.side_effect = [
            [], [Mock(spec = Invite)]
        ]
        self.mock_invite_dao.get_all_by_sender.return_value = []

        result, msg = self.manager.invite_user(sender_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, InviteManager.Result.failure)
        self.assertIn("Receiver '@receiver_username' already has an invitation", msg)

    def test_invite_user_failure_receiver_has_api_key(self):
        sender_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        receiver_user = Mock(spec = User, id = UUID(int = 2), open_ai_key = "receiver_api_key")
        self.mock_user_dao.get.return_value = self.user
        self.mock_invite_dao.get_all_by_sender.return_value = []
        self.mock_user_dao.get_by_telegram_username.return_value = receiver_user
        self.mock_invite_dao.get_all_by_receiver.return_value = []

        result, msg = self.manager.invite_user(sender_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, InviteManager.Result.failure)
        self.assertIn("already has an API key set up", msg)

    def test_uninvite_user_success(self):
        sender_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        sender_user_db = UserDB(**self.user.model_dump())
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

        # Create a mock invite
        invite_db = Invite(
            sender_id = sender_user_db.id,
            receiver_id = receiver_user_db.id,
            invited_at = datetime.now(),
            accepted_at = None,
        )

        self.mock_user_dao.get.side_effect = [sender_user_db, receiver_user_db]
        self.mock_user_dao.get_by_telegram_username.return_value = receiver_user_db
        self.mock_invite_dao.get.return_value = Mock(**invite_db.model_dump())

        result, msg = self.manager.uninvite_user(sender_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, InviteManager.Result.success)
        self.assertIn("Invite revoked", msg)
        self.mock_invite_dao.delete.assert_called_once_with(sender_user_db.id, receiver_user_db.id)
        self.mock_user_dao.save.assert_called()

    def test_uninvite_user_failure_sender_not_found(self):
        sender_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        self.mock_user_dao.get.side_effect = [None, None]

        result, msg = self.manager.uninvite_user(sender_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, InviteManager.Result.failure)
        self.assertIn("Sender '", msg)

    def test_uninvite_user_failure_no_invite(self):
        sender_user_id_hex = self.user.id.hex
        receiver_telegram_username = "receiver_username"

        sender_user_db = UserDB(**self.user.model_dump())
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

        self.mock_user_dao.get.side_effect = [sender_user_db, receiver_user_db]
        self.mock_user_dao.get_by_telegram_username.return_value = receiver_user_db
        self.mock_invite_dao.get.return_value = None

        result, msg = self.manager.uninvite_user(sender_user_id_hex, receiver_telegram_username)

        self.assertEqual(result, InviteManager.Result.failure)
        self.assertIn("has no invitation", msg)

    def test_accept_invite_failure_no_invite(self):
        self.mock_invite_dao.get_all_by_receiver.return_value = []

        result = self.manager.accept_invite(self.user)

        self.assertFalse(result)

    def test_accept_invite_failure_no_api_key(self):
        user_without_key = self.user.model_copy(update = {"open_ai_key": None})

        result = self.manager.accept_invite(user_without_key)

        self.assertFalse(result)

    def test_purge_accepted_invites(self):
        self.mock_invite_dao.delete_all_by_receiver.return_value = 2

        result = self.manager.purge_accepted_invites(self.user)

        self.assertEqual(result, 2)
        self.mock_invite_dao.delete_all_by_receiver.assert_called_once_with(self.user.id)
