import unittest
from datetime import datetime
from unittest.mock import Mock

from db.sql_util import SQLUtil
from pydantic import SecretStr

from db.model.chat_config import ChatConfigDB
from db.model.user import UserDB
from db.schema.chat_config import ChatConfig, ChatConfigSave
from db.schema.user import User, UserSave
from di.di import DI
from features.chat.membership.chat_membership import ChatMembership
from features.chat.membership.chat_membership_service import ChatMembershipService


class ChatMembershipServiceTest(unittest.TestCase):

    sql: SQLUtil
    mock_di: DI
    service: ChatMembershipService
    user: User
    chat: ChatConfig

    def setUp(self):
        self.sql = SQLUtil()
        self.user = User.model_validate(
            self.sql.user_crud().create(
                UserSave(
                    full_name = "Test User",
                    telegram_username = "testuser",
                    telegram_chat_id = "chat_ext_1",
                    telegram_user_id = 1,
                    open_ai_key = SecretStr("key"),
                    group = UserDB.Group.standard,
                    created_at = datetime.now().date(),
                ),
            ),
        )
        self.chat = ChatConfig.model_validate(
            self.sql.chat_config_crud().create(
                ChatConfigSave(
                    external_id = "chat_ext_1",
                    chat_type = ChatConfigDB.ChatType.telegram,
                    is_private = True,
                ),
            ),
        )
        self.mock_sdk = Mock()
        self.mock_sdk.resolve_member_is_admin.return_value = False
        self.mock_di = Mock(spec = DI)
        # noinspection PyPropertyAccess
        self.mock_di.chat_membership_repo = self.sql.chat_membership_repo()
        self.mock_di.platform_bot_sdk.return_value = self.mock_sdk
        self.service = ChatMembershipService(self.mock_di)

    def tearDown(self):
        self.sql.end_session()

    # === get ===

    def test_get_returns_none_when_missing(self):
        result = self.service.get(self.user.id, self.chat.chat_id)
        self.assertIsNone(result)

    def test_get_returns_existing_row(self):
        self.sql.chat_membership_repo().save(
            ChatMembership(
                user_id = self.user.id,
                chat_id = self.chat.chat_id,
                is_admin = True,
                use_about_me = False,
                use_custom_prompt = True,
            ),
        )

        result = self.service.get(self.user.id, self.chat.chat_id)

        self.assertIsNotNone(result)
        self.assertTrue(result.is_admin)
        self.assertFalse(result.use_about_me)
        self.assertTrue(result.use_custom_prompt)

    # === get_all_for_user ===

    def test_get_all_for_user_returns_empty_when_none(self):
        result = self.service.get_all_for_user(self.user.id)
        self.assertEqual(len(result), 0)

    def test_get_all_for_user_returns_all_rows(self):
        second_chat = ChatConfig.model_validate(
            self.sql.chat_config_crud().create(
                ChatConfigSave(external_id = "chat_ext_2", chat_type = ChatConfigDB.ChatType.telegram),
            ),
        )
        repo = self.sql.chat_membership_repo()
        repo.save(ChatMembership(user_id = self.user.id, chat_id = self.chat.chat_id))
        repo.save(ChatMembership(user_id = self.user.id, chat_id = second_chat.chat_id))

        result = self.service.get_all_for_user(self.user.id)

        self.assertEqual(len(result), 2)
        chat_ids = {r.chat_id for r in result}
        self.assertIn(self.chat.chat_id, chat_ids)
        self.assertIn(second_chat.chat_id, chat_ids)

    # === save ===

    def test_save_creates_new_row(self):
        membership = ChatMembership(
            user_id = self.user.id,
            chat_id = self.chat.chat_id,
            is_admin = True,
            use_about_me = False,
            use_custom_prompt = True,
        )

        result = self.service.save(membership)

        self.assertEqual(result.user_id, self.user.id)
        self.assertEqual(result.chat_id, self.chat.chat_id)
        self.assertTrue(result.is_admin)
        self.assertFalse(result.use_about_me)
        self.assertTrue(result.use_custom_prompt)

    def test_save_upserts_existing_row(self):
        self.sql.chat_membership_repo().save(
            ChatMembership(user_id = self.user.id, chat_id = self.chat.chat_id, is_admin = False),
        )

        result = self.service.save(
            ChatMembership(user_id = self.user.id, chat_id = self.chat.chat_id, is_admin = True),
        )

        self.assertTrue(result.is_admin)
        fetched = self.service.get(self.user.id, self.chat.chat_id)
        self.assertTrue(fetched.is_admin)

    # === get_or_create ===

    def test_get_or_create_returns_existing_without_platform_call(self):
        existing = self.sql.chat_membership_repo().save(
            ChatMembership(
                user_id = self.user.id,
                chat_id = self.chat.chat_id,
                is_admin = True,
                use_about_me = False,
                use_custom_prompt = False,
            ),
        )

        result = self.service.get_or_create(self.user, self.chat)

        self.assertEqual(result.user_id, existing.user_id)
        self.assertTrue(result.is_admin)
        self.assertFalse(result.use_about_me)
        self.mock_sdk.resolve_member_is_admin.assert_not_called()

    def test_get_or_create_creates_with_sdk_admin_true(self):
        self.mock_sdk.resolve_member_is_admin.return_value = True

        result = self.service.get_or_create(self.user, self.chat)

        self.assertEqual(result.user_id, self.user.id)
        self.assertEqual(result.chat_id, self.chat.chat_id)
        self.assertTrue(result.is_admin)
        self.assertTrue(result.use_about_me)
        self.assertTrue(result.use_custom_prompt)
        self.mock_sdk.resolve_member_is_admin.assert_called_once_with(self.chat, self.user)

    def test_get_or_create_creates_with_sdk_admin_false(self):
        self.mock_sdk.resolve_member_is_admin.return_value = False

        result = self.service.get_or_create(self.user, self.chat)

        self.assertFalse(result.is_admin)
        self.assertTrue(result.use_about_me)
        self.assertTrue(result.use_custom_prompt)
        stored = self.service.get(self.user.id, self.chat.chat_id)
        self.assertIsNotNone(stored)

    # === refresh_chat_memberships ===

    def test_refresh_chat_memberships_promotes_new_admin(self):
        result = self.service.refresh_chat_memberships(self.user, [self.chat])

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].is_admin)

    def test_refresh_chat_memberships_preserves_preferences_on_promote(self):
        self.sql.chat_membership_repo().save(
            ChatMembership(
                user_id = self.user.id,
                chat_id = self.chat.chat_id,
                is_admin = False,
                use_about_me = False,
                use_custom_prompt = False,
            ),
        )

        result = self.service.refresh_chat_memberships(self.user, [self.chat])

        self.assertTrue(result[0].is_admin)
        self.assertFalse(result[0].use_about_me)
        self.assertFalse(result[0].use_custom_prompt)

    def test_refresh_chat_memberships_demotes_stale_admin(self):
        self.sql.chat_membership_repo().save(
            ChatMembership(
                user_id = self.user.id,
                chat_id = self.chat.chat_id,
                is_admin = True,
                use_about_me = True,
                use_custom_prompt = True,
            ),
        )

        result = self.service.refresh_chat_memberships(self.user, [])

        self.assertEqual(len(result), 1)
        self.assertFalse(result[0].is_admin)
        self.assertTrue(result[0].use_about_me)
        self.assertTrue(result[0].use_custom_prompt)

    def test_refresh_chat_memberships_skips_already_correct_admin_row(self):
        self.sql.chat_membership_repo().save(
            ChatMembership(
                user_id = self.user.id,
                chat_id = self.chat.chat_id,
                is_admin = True,
            ),
        )

        self.service.refresh_chat_memberships(self.user, [self.chat])

        stored = self.service.get(self.user.id, self.chat.chat_id)
        self.assertTrue(stored.is_admin)

    def test_refresh_chat_memberships_creates_missing_admin_row_with_defaults(self):
        result = self.service.refresh_chat_memberships(self.user, [self.chat])

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].is_admin)
        self.assertTrue(result[0].use_about_me)
        self.assertTrue(result[0].use_custom_prompt)

    def test_refresh_chat_memberships_handles_multiple_chats(self):
        second_chat = ChatConfig.model_validate(
            self.sql.chat_config_crud().create(
                ChatConfigSave(external_id = "chat_ext_3", chat_type = ChatConfigDB.ChatType.telegram),
            ),
        )
        self.sql.chat_membership_repo().save(
            ChatMembership(user_id = self.user.id, chat_id = self.chat.chat_id, is_admin = True),
        )
        self.sql.chat_membership_repo().save(
            ChatMembership(user_id = self.user.id, chat_id = second_chat.chat_id, is_admin = False),
        )

        result = self.service.refresh_chat_memberships(self.user, [second_chat])

        by_chat = {m.chat_id: m for m in result}
        self.assertFalse(by_chat[self.chat.chat_id].is_admin)
        self.assertTrue(by_chat[second_chat.chat_id].is_admin)

    def test_refresh_chat_memberships_with_no_admin_chats_returns_empty(self):
        result = self.service.refresh_chat_memberships(self.user, [])

        self.assertEqual(len(result), 0)
