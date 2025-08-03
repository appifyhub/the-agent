import unittest
from datetime import datetime

from db.sql_util import SQLUtil

from db.schema.sponsorship import SponsorshipSave
from db.schema.user import UserSave


class SponsorshipCRUDTest(unittest.TestCase):

    sql: SQLUtil

    def setUp(self):
        self.sql = SQLUtil()

    def tearDown(self):
        self.sql.end_session()

    def test_create_sponsorship(self):
        sponsor = self.sql.user_crud().create(UserSave())
        receiver = self.sql.user_crud().create(UserSave())
        sponsorship_data = SponsorshipSave(
            sponsor_id = sponsor.id,
            receiver_id = receiver.id,
        )

        sponsorship = self.sql.sponsorship_crud().create(sponsorship_data)

        self.assertEqual(sponsorship.sponsor_id, sponsorship_data.sponsor_id)
        self.assertEqual(sponsorship.receiver_id, sponsorship_data.receiver_id)
        self.assertIsNotNone(sponsorship.sponsored_at)
        self.assertIsNone(sponsorship.accepted_at)

    def test_get_sponsorship(self):
        sponsor = self.sql.user_crud().create(UserSave())
        receiver = self.sql.user_crud().create(UserSave())
        sponsorship_data = SponsorshipSave(
            sponsor_id = sponsor.id,
            receiver_id = receiver.id,
        )
        created_sponsorship = self.sql.sponsorship_crud().create(sponsorship_data)

        fetched_sponsorship = self.sql.sponsorship_crud().get(sponsor.id, receiver.id)

        self.assertEqual(fetched_sponsorship.sponsor_id, created_sponsorship.sponsor_id)
        self.assertEqual(fetched_sponsorship.receiver_id, created_sponsorship.receiver_id)

    def test_get_all_by_sponsor(self):
        sponsor = self.sql.user_crud().create(UserSave())
        receiver1 = self.sql.user_crud().create(UserSave())
        receiver2 = self.sql.user_crud().create(UserSave())
        sponsorships = [
            self.sql.sponsorship_crud().create(SponsorshipSave(sponsor_id = sponsor.id, receiver_id = receiver1.id)),
            self.sql.sponsorship_crud().create(SponsorshipSave(sponsor_id = sponsor.id, receiver_id = receiver2.id)),
        ]

        fetched_sponsorships = self.sql.sponsorship_crud().get_all_by_sponsor(sponsor.id)

        self.assertEqual(len(fetched_sponsorships), len(sponsorships))
        for sponsorship in fetched_sponsorships:
            self.assertEqual(sponsorship.sponsor_id, sponsor.id)
            self.assertIn(sponsorship.receiver_id, [receiver1.id, receiver2.id])

    def test_get_all_by_receiver(self):
        receiver = self.sql.user_crud().create(UserSave())
        sponsor1 = self.sql.user_crud().create(UserSave())
        sponsor2 = self.sql.user_crud().create(UserSave())
        sponsorships = [
            self.sql.sponsorship_crud().create(SponsorshipSave(sponsor_id = sponsor1.id, receiver_id = receiver.id)),
            self.sql.sponsorship_crud().create(SponsorshipSave(sponsor_id = sponsor2.id, receiver_id = receiver.id)),
        ]

        fetched_sponsorships = self.sql.sponsorship_crud().get_all_by_receiver(receiver.id)

        self.assertEqual(len(fetched_sponsorships), len(sponsorships))
        for sponsorship in fetched_sponsorships:
            self.assertEqual(sponsorship.receiver_id, receiver.id)
            self.assertIn(sponsorship.sponsor_id, [sponsor1.id, sponsor2.id])

    def test_get_all_sponsorships(self):
        sponsor1 = self.sql.user_crud().create(UserSave())
        receiver1 = self.sql.user_crud().create(UserSave())
        sponsor2 = self.sql.user_crud().create(UserSave())
        receiver2 = self.sql.user_crud().create(UserSave())
        sponsorships = [
            self.sql.sponsorship_crud().create(SponsorshipSave(sponsor_id = sponsor1.id, receiver_id = receiver1.id)),
            self.sql.sponsorship_crud().create(SponsorshipSave(sponsor_id = sponsor2.id, receiver_id = receiver2.id)),
        ]

        fetched_sponsorships = self.sql.sponsorship_crud().get_all()

        self.assertEqual(len(fetched_sponsorships), len(sponsorships))
        for i in range(len(sponsorships)):
            self.assertEqual(fetched_sponsorships[i].sponsor_id, sponsorships[i].sponsor_id)
            self.assertEqual(fetched_sponsorships[i].receiver_id, sponsorships[i].receiver_id)

    def test_update_sponsorship(self):
        sponsor = self.sql.user_crud().create(UserSave())
        receiver = self.sql.user_crud().create(UserSave())
        sponsorship_data = SponsorshipSave(
            sponsor_id = sponsor.id,
            receiver_id = receiver.id,
        )
        created_sponsorship = self.sql.sponsorship_crud().create(sponsorship_data)

        update_data = SponsorshipSave(
            sponsor_id = sponsor.id,
            receiver_id = receiver.id,
            accepted_at = datetime.now(),
        )
        updated_sponsorship = self.sql.sponsorship_crud().update(update_data)

        self.assertEqual(updated_sponsorship.sponsor_id, created_sponsorship.sponsor_id)
        self.assertEqual(updated_sponsorship.receiver_id, created_sponsorship.receiver_id)
        self.assertIsNotNone(updated_sponsorship.accepted_at, created_sponsorship.sponsored_at)
        self.assertEqual(updated_sponsorship.accepted_at, update_data.accepted_at)

    def test_save_sponsorship(self):
        sponsor = self.sql.user_crud().create(UserSave())
        receiver = self.sql.user_crud().create(UserSave())
        sponsorship_data = SponsorshipSave(
            sponsor_id = sponsor.id,
            receiver_id = receiver.id,
        )

        # First, save should create the record
        saved_sponsorship = self.sql.sponsorship_crud().save(sponsorship_data)
        self.assertIsNotNone(saved_sponsorship)
        self.assertEqual(saved_sponsorship.sponsor_id, sponsorship_data.sponsor_id)
        self.assertEqual(saved_sponsorship.receiver_id, sponsorship_data.receiver_id)
        self.assertIsNotNone(saved_sponsorship.sponsored_at)
        self.assertIsNone(saved_sponsorship.accepted_at)

        # Now, save should update the existing record
        update_data = SponsorshipSave(
            sponsor_id = sponsor.id,
            receiver_id = receiver.id,
            accepted_at = datetime.now(),
        )
        updated_sponsorship = self.sql.sponsorship_crud().save(update_data)
        self.assertIsNotNone(updated_sponsorship)
        self.assertEqual(updated_sponsorship.sponsor_id, sponsorship_data.sponsor_id)
        self.assertEqual(updated_sponsorship.receiver_id, sponsorship_data.receiver_id)
        self.assertIsNotNone(updated_sponsorship.sponsored_at)
        self.assertEqual(updated_sponsorship.accepted_at, update_data.accepted_at)

    def test_delete_sponsorship(self):
        sponsor = self.sql.user_crud().create(UserSave())
        receiver = self.sql.user_crud().create(UserSave())
        sponsorship_data = SponsorshipSave(
            sponsor_id = sponsor.id,
            receiver_id = receiver.id,
        )
        created_sponsorship = self.sql.sponsorship_crud().create(sponsorship_data)

        deleted_sponsorship = self.sql.sponsorship_crud().delete(sponsor.id, receiver.id)

        self.assertEqual(deleted_sponsorship.sponsor_id, created_sponsorship.sponsor_id)
        self.assertEqual(deleted_sponsorship.receiver_id, created_sponsorship.receiver_id)
        self.assertIsNone(self.sql.sponsorship_crud().get(sponsor.id, receiver.id))

    def test_delete_all_by_receiver(self):
        receiver = self.sql.user_crud().create(UserSave())

        sponsor1 = self.sql.user_crud().create(UserSave())
        sponsor2 = self.sql.user_crud().create(UserSave())
        self.sql.sponsorship_crud().create(SponsorshipSave(sponsor_id = sponsor1.id, receiver_id = receiver.id))
        self.sql.sponsorship_crud().create(SponsorshipSave(sponsor_id = sponsor2.id, receiver_id = receiver.id))

        deleted_count = self.sql.sponsorship_crud().delete_all_by_receiver(receiver.id)

        self.assertEqual(deleted_count, 2)
        remaining_sponsorships = self.sql.sponsorship_crud().get_all_by_receiver(receiver.id)
        self.assertEqual(len(remaining_sponsorships), 0)
