import unittest
from datetime import datetime

from db.schema.invite import InviteSave
from db.schema.user import UserSave
from db.sql_util import SQLUtil


class InviteCRUDTest(unittest.TestCase):
    sql: SQLUtil

    def setUp(self):
        self.sql = SQLUtil()

    def tearDown(self):
        self.sql.end_session()

    def test_create_invite(self):
        sender = self.sql.user_crud().create(UserSave())
        receiver = self.sql.user_crud().create(UserSave())
        invite_data = InviteSave(
            sender_id = sender.id,
            receiver_id = receiver.id,
        )

        invite = self.sql.invite_crud().create(invite_data)

        self.assertEqual(invite.sender_id, invite_data.sender_id)
        self.assertEqual(invite.receiver_id, invite_data.receiver_id)
        self.assertIsNotNone(invite.invited_at)
        self.assertIsNone(invite.accepted_at)

    def test_get_invite(self):
        sender = self.sql.user_crud().create(UserSave())
        receiver = self.sql.user_crud().create(UserSave())
        invite_data = InviteSave(
            sender_id = sender.id,
            receiver_id = receiver.id,
        )
        created_invite = self.sql.invite_crud().create(invite_data)

        fetched_invite = self.sql.invite_crud().get(sender.id, receiver.id)

        self.assertEqual(fetched_invite.sender_id, created_invite.sender_id)
        self.assertEqual(fetched_invite.receiver_id, created_invite.receiver_id)

    def test_get_all_by_sender(self):
        sender = self.sql.user_crud().create(UserSave())
        receiver1 = self.sql.user_crud().create(UserSave())
        receiver2 = self.sql.user_crud().create(UserSave())
        invites = [
            self.sql.invite_crud().create(InviteSave(sender_id = sender.id, receiver_id = receiver1.id)),
            self.sql.invite_crud().create(InviteSave(sender_id = sender.id, receiver_id = receiver2.id)),
        ]

        fetched_invites = self.sql.invite_crud().get_all_by_sender(sender.id)

        self.assertEqual(len(fetched_invites), len(invites))
        for invite in fetched_invites:
            self.assertEqual(invite.sender_id, sender.id)
            self.assertIn(invite.receiver_id, [receiver1.id, receiver2.id])

    def test_get_all_by_receiver(self):
        receiver = self.sql.user_crud().create(UserSave())
        sender1 = self.sql.user_crud().create(UserSave())
        sender2 = self.sql.user_crud().create(UserSave())
        invites = [
            self.sql.invite_crud().create(InviteSave(sender_id = sender1.id, receiver_id = receiver.id)),
            self.sql.invite_crud().create(InviteSave(sender_id = sender2.id, receiver_id = receiver.id)),
        ]

        fetched_invites = self.sql.invite_crud().get_all_by_receiver(receiver.id)

        self.assertEqual(len(fetched_invites), len(invites))
        for invite in fetched_invites:
            self.assertEqual(invite.receiver_id, receiver.id)
            self.assertIn(invite.sender_id, [sender1.id, sender2.id])

    def test_get_all_invites(self):
        sender1 = self.sql.user_crud().create(UserSave())
        receiver1 = self.sql.user_crud().create(UserSave())
        sender2 = self.sql.user_crud().create(UserSave())
        receiver2 = self.sql.user_crud().create(UserSave())
        invites = [
            self.sql.invite_crud().create(InviteSave(sender_id = sender1.id, receiver_id = receiver1.id)),
            self.sql.invite_crud().create(InviteSave(sender_id = sender2.id, receiver_id = receiver2.id)),
        ]

        fetched_invites = self.sql.invite_crud().get_all()

        self.assertEqual(len(fetched_invites), len(invites))
        for i in range(len(invites)):
            self.assertEqual(fetched_invites[i].sender_id, invites[i].sender_id)
            self.assertEqual(fetched_invites[i].receiver_id, invites[i].receiver_id)

    def test_update_invite(self):
        sender = self.sql.user_crud().create(UserSave())
        receiver = self.sql.user_crud().create(UserSave())
        invite_data = InviteSave(
            sender_id = sender.id,
            receiver_id = receiver.id,
        )
        created_invite = self.sql.invite_crud().create(invite_data)

        update_data = InviteSave(
            sender_id = sender.id,
            receiver_id = receiver.id,
            accepted_at = datetime.now(),
        )
        updated_invite = self.sql.invite_crud().update(update_data)

        self.assertEqual(updated_invite.sender_id, created_invite.sender_id)
        self.assertEqual(updated_invite.receiver_id, created_invite.receiver_id)
        self.assertIsNotNone(updated_invite.invited_at, created_invite.invited_at)
        self.assertEqual(updated_invite.accepted_at, update_data.accepted_at)

    def test_save_invite(self):
        sender = self.sql.user_crud().create(UserSave())
        receiver = self.sql.user_crud().create(UserSave())
        invite_data = InviteSave(
            sender_id = sender.id,
            receiver_id = receiver.id,
        )

        # First, save should create the record
        saved_invite = self.sql.invite_crud().save(invite_data)
        self.assertIsNotNone(saved_invite)
        self.assertEqual(saved_invite.sender_id, invite_data.sender_id)
        self.assertEqual(saved_invite.receiver_id, invite_data.receiver_id)
        self.assertIsNotNone(saved_invite.invited_at)
        self.assertIsNone(saved_invite.accepted_at)

        # Now, save should update the existing record
        update_data = InviteSave(
            sender_id = sender.id,
            receiver_id = receiver.id,
            accepted_at = datetime.now(),
        )
        updated_invite = self.sql.invite_crud().save(update_data)
        self.assertIsNotNone(updated_invite)
        self.assertEqual(updated_invite.sender_id, invite_data.sender_id)
        self.assertEqual(updated_invite.receiver_id, invite_data.receiver_id)
        self.assertIsNotNone(updated_invite.invited_at)
        self.assertEqual(updated_invite.accepted_at, update_data.accepted_at)

    def test_delete_invite(self):
        sender = self.sql.user_crud().create(UserSave())
        receiver = self.sql.user_crud().create(UserSave())
        invite_data = InviteSave(
            sender_id = sender.id,
            receiver_id = receiver.id,
        )
        created_invite = self.sql.invite_crud().create(invite_data)

        deleted_invite = self.sql.invite_crud().delete(sender.id, receiver.id)

        self.assertEqual(deleted_invite.sender_id, created_invite.sender_id)
        self.assertEqual(deleted_invite.receiver_id, created_invite.receiver_id)
        self.assertIsNone(self.sql.invite_crud().get(sender.id, receiver.id))

    def test_delete_all_by_receiver(self):
        receiver = self.sql.user_crud().create(UserSave())

        sender1 = self.sql.user_crud().create(UserSave())
        sender2 = self.sql.user_crud().create(UserSave())
        self.sql.invite_crud().create(InviteSave(sender_id = sender1.id, receiver_id = receiver.id))
        self.sql.invite_crud().create(InviteSave(sender_id = sender2.id, receiver_id = receiver.id))

        deleted_count = self.sql.invite_crud().delete_all_by_receiver(receiver.id)

        self.assertEqual(deleted_count, 2)
        remaining_invites = self.sql.invite_crud().get_all_by_receiver(receiver.id)
        self.assertEqual(len(remaining_invites), 0)
