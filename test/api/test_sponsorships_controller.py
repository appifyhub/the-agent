import unittest
from datetime import datetime
from unittest.mock import Mock, patch
from uuid import UUID

from api.sponsorships_controller import SponsorshipsController
from db.crud.chat_config import ChatConfigCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.model.sponsorship import SponsorshipDB
from db.model.user import UserDB
from db.schema.sponsorship import Sponsorship
from db.schema.user import User
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.sponsorships.sponsorship_service import SponsorshipService
from util.config import config


class SponsorshipsControllerTest(unittest.TestCase):
    invoker_user: User
    sponsor_user: User
    receiver_user: User
    sponsorship: Sponsorship
    mock_user_dao: UserCRUD
    mock_sponsorship_dao: SponsorshipCRUD
    mock_chat_config_dao: ChatConfigCRUD
    mock_telegram_sdk: TelegramBotSDK

    def setUp(self):
        self.invoker_user = User(
            id = UUID(int = 1),
            full_name = "Invoker User",
            telegram_username = "invoker_username",
            telegram_chat_id = "invoker_chat_id",
            telegram_user_id = 1,
            open_ai_key = "invoker_api_key",
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.sponsor_user = User(
            id = UUID(int = 2),
            full_name = "Sponsor User",
            telegram_username = "sponsor_username",
            telegram_chat_id = "sponsor_chat_id",
            telegram_user_id = 2,
            open_ai_key = "sponsor_api_key",
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.receiver_user = User(
            id = UUID(int = 3),
            full_name = "Receiver User",
            telegram_username = "receiver_username",
            telegram_chat_id = "receiver_chat_id",
            telegram_user_id = 3,
            open_ai_key = "receiver_api_key",
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.sponsorship = Sponsorship(
            sponsor_id = self.sponsor_user.id,
            receiver_id = self.receiver_user.id,
            sponsored_at = datetime.now(),
            accepted_at = datetime.now(),
        )
        self.mock_user_dao = Mock(spec = UserCRUD)
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_sponsorship_dao = Mock(spec = SponsorshipCRUD)
        self.mock_chat_config_dao = Mock(spec = ChatConfigCRUD)
        self.mock_telegram_sdk = Mock(spec = TelegramBotSDK)

    def test_init_success(self):
        with patch("api.sponsorships_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user

            SponsorshipsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                user_dao = self.mock_user_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
                telegram_sdk = self.mock_telegram_sdk,
                chat_config_dao = self.mock_chat_config_dao,
            )

            # invoker_user is now private, so we can't directly access it
            # Just verify the validation was called correctly
            mock_auth_service.validate_user.assert_called_once_with(self.invoker_user.id.hex)

    def test_init_failure_invalid_user(self):
        with patch("api.sponsorships_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.side_effect = ValueError("User not found")

            with self.assertRaises(ValueError) as context:
                SponsorshipsController(
                    invoker_user_id_hex = self.invoker_user.id.hex,
                    user_dao = self.mock_user_dao,
                    sponsorship_dao = self.mock_sponsorship_dao,
                    telegram_sdk = self.mock_telegram_sdk,
                    chat_config_dao = self.mock_chat_config_dao,
                )
            self.assertIn("User not found", str(context.exception))

    def test_fetch_sponsorships_success_with_sponsorships(self):
        sponsorship_db = SponsorshipDB(
            sponsor_id = self.sponsorship.sponsor_id,
            receiver_id = self.sponsorship.receiver_id,
            sponsored_at = self.sponsorship.sponsored_at,
            accepted_at = self.sponsorship.accepted_at,
        )
        receiver_user_db = UserDB(
            id = self.receiver_user.id,
            full_name = self.receiver_user.full_name,
            telegram_username = self.receiver_user.telegram_username,
            telegram_chat_id = self.receiver_user.telegram_chat_id,
            telegram_user_id = self.receiver_user.telegram_user_id,
            open_ai_key = self.receiver_user.open_ai_key,
            group = self.receiver_user.group,
            created_at = self.receiver_user.created_at,
        )

        self.mock_sponsorship_dao.get_all_by_sponsor.return_value = [sponsorship_db]
        self.mock_user_dao.get.return_value = receiver_user_db

        with patch("api.sponsorships_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_user.return_value = self.sponsor_user

            controller = SponsorshipsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                user_dao = self.mock_user_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
                telegram_sdk = self.mock_telegram_sdk,
                chat_config_dao = self.mock_chat_config_dao,
            )
            result = controller.fetch_sponsorships(self.sponsor_user.id.hex)

            self.assertIsInstance(result, dict)
            self.assertIn("sponsorships", result)
            self.assertIn("max_sponsorships", result)
            self.assertEqual(len(result["sponsorships"]), 1)
            self.assertEqual(result["sponsorships"][0]["full_name"], self.receiver_user.full_name)
            self.assertEqual(result["sponsorships"][0]["telegram_username"], self.receiver_user.telegram_username)
            self.assertIsNotNone(result["sponsorships"][0]["sponsored_at"])
            self.assertIsNotNone(result["sponsorships"][0]["accepted_at"])
            # For standard users, should get max_sponsorships_per_user
            self.assertEqual(result["max_sponsorships"], config.max_sponsorships_per_user)
            mock_auth_service.authorize_for_user.assert_called_once_with(self.invoker_user, self.sponsor_user.id.hex)
            # noinspection PyUnresolvedReferences
            self.mock_sponsorship_dao.get_all_by_sponsor.assert_called_once_with(self.sponsor_user.id)

    def test_fetch_sponsorships_success_no_sponsorships(self):
        self.mock_sponsorship_dao.get_all_by_sponsor.return_value = []

        with patch("api.sponsorships_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_user.return_value = self.sponsor_user

            controller = SponsorshipsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                user_dao = self.mock_user_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
                telegram_sdk = self.mock_telegram_sdk,
                chat_config_dao = self.mock_chat_config_dao,
            )
            result = controller.fetch_sponsorships(self.sponsor_user.id.hex)

            self.assertIsInstance(result, dict)
            self.assertIn("sponsorships", result)
            self.assertIn("max_sponsorships", result)
            self.assertEqual(len(result["sponsorships"]), 0)
            # For standard users, should get max_sponsorships_per_user
            self.assertEqual(result["max_sponsorships"], config.max_sponsorships_per_user)
            # noinspection PyUnresolvedReferences
            self.mock_sponsorship_dao.get_all_by_sponsor.assert_called_once_with(self.sponsor_user.id)

    def test_fetch_sponsorships_success_with_missing_receiver(self):
        sponsorship_db = SponsorshipDB(
            sponsor_id = self.sponsorship.sponsor_id,
            receiver_id = self.sponsorship.receiver_id,
            sponsored_at = self.sponsorship.sponsored_at,
            accepted_at = self.sponsorship.accepted_at,
        )
        self.mock_sponsorship_dao.get_all_by_sponsor.return_value = [sponsorship_db]
        self.mock_user_dao.get.return_value = None  # Receiver user not found

        with patch("api.sponsorships_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_user.return_value = self.sponsor_user

            controller = SponsorshipsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                user_dao = self.mock_user_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
                telegram_sdk = self.mock_telegram_sdk,
                chat_config_dao = self.mock_chat_config_dao,
            )
            result = controller.fetch_sponsorships(self.sponsor_user.id.hex)

            self.assertIsInstance(result, dict)
            self.assertIn("sponsorships", result)
            self.assertIn("max_sponsorships", result)
            self.assertEqual(len(result["sponsorships"]), 0)  # Should skip missing receiver
            # For standard users, should get max_sponsorships_per_user
            self.assertEqual(result["max_sponsorships"], config.max_sponsorships_per_user)

    def test_fetch_sponsorships_success_with_null_accepted_at(self):
        # noinspection PyTypeChecker
        sponsorship_db = SponsorshipDB(
            sponsor_id = self.sponsorship.sponsor_id,
            receiver_id = self.sponsorship.receiver_id,
            sponsored_at = self.sponsorship.sponsored_at,
            accepted_at = None,  # Not accepted yet
        )
        receiver_user_db = UserDB(
            id = self.receiver_user.id,
            full_name = self.receiver_user.full_name,
            telegram_username = self.receiver_user.telegram_username,
            telegram_chat_id = self.receiver_user.telegram_chat_id,
            telegram_user_id = self.receiver_user.telegram_user_id,
            open_ai_key = self.receiver_user.open_ai_key,
            group = self.receiver_user.group,
            created_at = self.receiver_user.created_at,
        )

        self.mock_sponsorship_dao.get_all_by_sponsor.return_value = [sponsorship_db]
        self.mock_user_dao.get.return_value = receiver_user_db

        with patch("api.sponsorships_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_user.return_value = self.sponsor_user

            controller = SponsorshipsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                user_dao = self.mock_user_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
                telegram_sdk = self.mock_telegram_sdk,
                chat_config_dao = self.mock_chat_config_dao,
            )
            result = controller.fetch_sponsorships(self.sponsor_user.id.hex)

            self.assertIsInstance(result, dict)
            self.assertIn("sponsorships", result)
            self.assertIn("max_sponsorships", result)
            self.assertEqual(len(result["sponsorships"]), 1)
            self.assertIsNotNone(result["sponsorships"][0]["sponsored_at"])
            self.assertEqual(result["sponsorships"][0]["accepted_at"], None)
            # For standard users, should get max_sponsorships_per_user
            self.assertEqual(result["max_sponsorships"], config.max_sponsorships_per_user)

    def test_fetch_sponsorships_success_with_developer_user(self):
        developer_user = self.invoker_user.model_copy(update = {"group": UserDB.Group.developer})
        sponsorship_db = SponsorshipDB(
            sponsor_id = self.sponsorship.sponsor_id,
            receiver_id = self.sponsorship.receiver_id,
            sponsored_at = self.sponsorship.sponsored_at,
            accepted_at = self.sponsorship.accepted_at,
        )
        receiver_user_db = UserDB(
            id = self.receiver_user.id,
            full_name = self.receiver_user.full_name,
            telegram_username = self.receiver_user.telegram_username,
            telegram_chat_id = self.receiver_user.telegram_chat_id,
            telegram_user_id = self.receiver_user.telegram_user_id,
            open_ai_key = self.receiver_user.open_ai_key,
            group = self.receiver_user.group,
            created_at = self.receiver_user.created_at,
        )

        self.mock_sponsorship_dao.get_all_by_sponsor.return_value = [sponsorship_db]
        self.mock_user_dao.get.return_value = receiver_user_db

        with patch("api.sponsorships_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = developer_user
            mock_auth_service.authorize_for_user.return_value = self.sponsor_user

            controller = SponsorshipsController(
                invoker_user_id_hex = developer_user.id.hex,
                user_dao = self.mock_user_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
                telegram_sdk = self.mock_telegram_sdk,
                chat_config_dao = self.mock_chat_config_dao,
            )
            result = controller.fetch_sponsorships(self.sponsor_user.id.hex)

            self.assertIsInstance(result, dict)
            self.assertIn("sponsorships", result)
            self.assertIn("max_sponsorships", result)
            self.assertEqual(len(result["sponsorships"]), 1)
            # For developer users, should get max_users
            self.assertEqual(result["max_sponsorships"], config.max_users)

    def test_fetch_sponsorships_failure_unauthorized(self):
        with patch("api.sponsorships_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_user.side_effect = ValueError("Unauthorized")

            controller = SponsorshipsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                user_dao = self.mock_user_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
                telegram_sdk = self.mock_telegram_sdk,
                chat_config_dao = self.mock_chat_config_dao,
            )

            with self.assertRaises(ValueError) as context:
                controller.fetch_sponsorships(self.sponsor_user.id.hex)
            self.assertIn("Unauthorized", str(context.exception))

    @patch.object(SponsorshipService, "sponsor_user", return_value = (SponsorshipService.Result.success, "Success"))
    def test_sponsor_user_success(self, mock_sponsor_user):
        with patch("api.sponsorships_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_user.return_value = self.sponsor_user

            controller = SponsorshipsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                user_dao = self.mock_user_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
                telegram_sdk = self.mock_telegram_sdk,
                chat_config_dao = self.mock_chat_config_dao,
            )

            controller.sponsor_user(
                sponsor_user_id_hex = self.sponsor_user.id.hex,
                receiver_telegram_username = self.receiver_user.telegram_username,
            )

            mock_sponsor_user.assert_called_once_with(
                sponsor_user_id_hex = self.sponsor_user.id.hex,
                receiver_telegram_username = self.receiver_user.telegram_username,
            )

    # noinspection PyUnusedLocal
    @patch.object(
        SponsorshipService,
        "sponsor_user",
        return_value = (SponsorshipService.Result.failure, "User already sponsored"),
    )
    def test_sponsor_user_failure_already_sponsored(self, mock_sponsor_user):
        with patch("api.sponsorships_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_user.return_value = self.sponsor_user

            controller = SponsorshipsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                user_dao = self.mock_user_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
                telegram_sdk = self.mock_telegram_sdk,
                chat_config_dao = self.mock_chat_config_dao,
            )

            with self.assertRaises(ValueError) as context:
                controller.sponsor_user(
                    sponsor_user_id_hex = self.sponsor_user.id.hex,
                    receiver_telegram_username = self.receiver_user.telegram_username,
                )
            self.assertIn("User already sponsored", str(context.exception))

    def test_sponsor_user_failure_unauthorized(self):
        with patch("api.sponsorships_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_user.side_effect = ValueError("Unauthorized")

            controller = SponsorshipsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                user_dao = self.mock_user_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
                telegram_sdk = self.mock_telegram_sdk,
                chat_config_dao = self.mock_chat_config_dao,
            )

            with self.assertRaises(ValueError) as context:
                controller.sponsor_user(
                    sponsor_user_id_hex = self.sponsor_user.id.hex,
                    receiver_telegram_username = self.receiver_user.telegram_username,
                )
            self.assertIn("Unauthorized", str(context.exception))

    @patch.object(SponsorshipService, "unsponsor_user", return_value = (SponsorshipService.Result.success, "Success"))
    def test_unsponsor_user_success(self, mock_unsponsor_user):
        with patch("api.sponsorships_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_user.return_value = self.sponsor_user

            controller = SponsorshipsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                user_dao = self.mock_user_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
                telegram_sdk = self.mock_telegram_sdk,
                chat_config_dao = self.mock_chat_config_dao,
            )

            controller.unsponsor_user(
                sponsor_user_id_hex = self.sponsor_user.id.hex,
                receiver_telegram_username = self.receiver_user.telegram_username,
            )

            mock_unsponsor_user.assert_called_once_with(
                sponsor_user_id_hex = self.sponsor_user.id.hex,
                receiver_telegram_username = self.receiver_user.telegram_username,
            )

    # noinspection PyUnusedLocal
    @patch.object(
        SponsorshipService,
        "unsponsor_user",
        return_value = (SponsorshipService.Result.failure, "Sponsorship not found"),
    )
    def test_unsponsor_user_failure_not_found(self, mock_unsponsor_user):
        with patch("api.sponsorships_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_user.return_value = self.sponsor_user

            controller = SponsorshipsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                user_dao = self.mock_user_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
                telegram_sdk = self.mock_telegram_sdk,
                chat_config_dao = self.mock_chat_config_dao,
            )

            with self.assertRaises(ValueError) as context:
                controller.unsponsor_user(
                    sponsor_user_id_hex = self.sponsor_user.id.hex,
                    receiver_telegram_username = self.receiver_user.telegram_username,
                )
            self.assertIn("Sponsorship not found", str(context.exception))

    def test_unsponsor_user_failure_unauthorized(self):
        with patch("api.sponsorships_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_user.side_effect = ValueError("Unauthorized")

            controller = SponsorshipsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                user_dao = self.mock_user_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
                telegram_sdk = self.mock_telegram_sdk,
                chat_config_dao = self.mock_chat_config_dao,
            )

            with self.assertRaises(ValueError) as context:
                controller.unsponsor_user(
                    sponsor_user_id_hex = self.sponsor_user.id.hex,
                    receiver_telegram_username = self.receiver_user.telegram_username,
                )
            self.assertIn("Unauthorized", str(context.exception))

    @patch.object(SponsorshipService, "unsponsor_self", return_value = (SponsorshipService.Result.success, "Success"))
    def test_unsponsor_self_success(self, mock_unsponsor_self):
        with patch("api.sponsorships_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_user.return_value = self.receiver_user

            controller = SponsorshipsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                user_dao = self.mock_user_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
                telegram_sdk = self.mock_telegram_sdk,
                chat_config_dao = self.mock_chat_config_dao,
            )

            controller.unsponsor_self(self.receiver_user.id.hex)

            mock_unsponsor_self.assert_called_once_with(self.receiver_user.id.hex)

    # noinspection PyUnusedLocal
    @patch.object(
        SponsorshipService,
        "unsponsor_self",
        return_value = (SponsorshipService.Result.failure, "No sponsorships to remove"),
    )
    def test_unsponsor_self_failure_no_sponsorships(self, mock_unsponsor_self):
        with patch("api.sponsorships_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_user.return_value = self.receiver_user

            controller = SponsorshipsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                user_dao = self.mock_user_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
                telegram_sdk = self.mock_telegram_sdk,
                chat_config_dao = self.mock_chat_config_dao,
            )

            with self.assertRaises(ValueError) as context:
                controller.unsponsor_self(self.receiver_user.id.hex)
            self.assertIn("No sponsorships to remove", str(context.exception))

    def test_unsponsor_self_failure_unauthorized(self):
        with patch("api.sponsorships_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_user.side_effect = ValueError("Unauthorized")

            controller = SponsorshipsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                user_dao = self.mock_user_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
                telegram_sdk = self.mock_telegram_sdk,
                chat_config_dao = self.mock_chat_config_dao,
            )

            with self.assertRaises(ValueError) as context:
                controller.unsponsor_self(self.receiver_user.id.hex)
            self.assertIn("Unauthorized", str(context.exception))
