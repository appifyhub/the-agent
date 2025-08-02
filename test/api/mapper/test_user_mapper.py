import unittest
from datetime import date
from uuid import UUID

from pydantic import SecretStr

from api.mapper.user_mapper import api_to_domain, domain_to_api
from api.model.user_settings_payload import UserSettingsPayload
from db.model.user import UserDB
from db.schema.user import User
from util.functions import mask_secret


class UserMapperTest(unittest.TestCase):
    user: User

    def setUp(self):
        self.user = User(
            id = UUID("12345678-1234-5678-1234-567812345678"),
            full_name = "Test User",
            telegram_username = "testuser",
            telegram_chat_id = "123456789",
            telegram_user_id = 123456789,
            open_ai_key = SecretStr("sk-test123"),
            anthropic_key = SecretStr("sk-ant-test456"),
            google_ai_key = SecretStr("google-test789"),
            perplexity_key = SecretStr("pplx-test789"),
            replicate_key = SecretStr("r8_test012"),
            rapid_api_key = SecretStr("rapid-test345"),
            coinmarketcap_key = SecretStr("cmc-test678"),
            tool_choice_chat = "gpt-4o",
            tool_choice_reasoning = "claude-3-5-sonnet-latest",
            tool_choice_copywriting = "gpt-4o-mini",
            tool_choice_vision = "gpt-4o",
            tool_choice_hearing = "whisper-1",
            tool_choice_images_gen = "dall-e-3",
            tool_choice_images_edit = "dall-e-2",
            tool_choice_images_restoration = "replicate-restoration",
            tool_choice_images_inpainting = "replicate-inpainting",
            tool_choice_images_background_removal = "replicate-background",
            tool_choice_search = "perplexity-online",
            tool_choice_embedding = "text-embedding-3-large",
            tool_choice_api_fiat_exchange = "rapid-api-fiat",
            tool_choice_api_crypto_exchange = "coinmarketcap-crypto",
            tool_choice_api_twitter = "rapid-api-twitter",
            group = UserDB.Group.standard,
            created_at = date(2024, 1, 1),
        )

    def test_api_to_domain_with_all_fields(self):
        payload = UserSettingsPayload(
            open_ai_key = "sk-new123",
            anthropic_key = "sk-ant-new456",
            google_ai_key = "google-new789",
            perplexity_key = "pplx-new789",
            replicate_key = "r8_new012",
            rapid_api_key = "rapid-new345",
            coinmarketcap_key = "cmc-new678",
            tool_choice_chat = "gpt-4o-mini",
            tool_choice_reasoning = "claude-3-opus-latest",
            tool_choice_copywriting = "gpt-4o",
            tool_choice_vision = "gpt-4o-mini",
            tool_choice_hearing = "whisper-1-turbo",
            tool_choice_images_gen = "dall-e-3-hd",
            tool_choice_images_edit = "dall-e-3",
            tool_choice_images_restoration = "new-restoration",
            tool_choice_images_inpainting = "new-inpainting",
            tool_choice_images_background_removal = "new-background",
            tool_choice_search = "perplexity-pro",
            tool_choice_embedding = "text-embedding-3-small",
            tool_choice_api_fiat_exchange = "new-fiat-api",
            tool_choice_api_crypto_exchange = "new-crypto-api",
            tool_choice_api_twitter = "new-twitter-api",
        )

        user_save = api_to_domain(payload, self.user)

        # Check that all fields were updated
        self.assertEqual(user_save.open_ai_key.get_secret_value() if user_save.open_ai_key else None, "sk-new123")
        self.assertEqual(user_save.anthropic_key.get_secret_value() if user_save.anthropic_key else None, "sk-ant-new456")
        self.assertEqual(user_save.google_ai_key.get_secret_value() if user_save.google_ai_key else None, "google-new789")
        self.assertEqual(user_save.perplexity_key.get_secret_value() if user_save.perplexity_key else None, "pplx-new789")
        self.assertEqual(user_save.replicate_key.get_secret_value() if user_save.replicate_key else None, "r8_new012")
        self.assertEqual(user_save.rapid_api_key.get_secret_value() if user_save.rapid_api_key else None, "rapid-new345")
        self.assertEqual(user_save.coinmarketcap_key.get_secret_value() if user_save.coinmarketcap_key else None, "cmc-new678")
        self.assertEqual(user_save.tool_choice_chat, "gpt-4o-mini")
        self.assertEqual(user_save.tool_choice_reasoning, "claude-3-opus-latest")
        self.assertEqual(user_save.tool_choice_copywriting, "gpt-4o")
        self.assertEqual(user_save.tool_choice_vision, "gpt-4o-mini")
        self.assertEqual(user_save.tool_choice_hearing, "whisper-1-turbo")
        self.assertEqual(user_save.tool_choice_images_gen, "dall-e-3-hd")
        self.assertEqual(user_save.tool_choice_images_edit, "dall-e-3")
        self.assertEqual(user_save.tool_choice_images_restoration, "new-restoration")
        self.assertEqual(user_save.tool_choice_images_inpainting, "new-inpainting")
        self.assertEqual(user_save.tool_choice_images_background_removal, "new-background")
        self.assertEqual(user_save.tool_choice_search, "perplexity-pro")
        self.assertEqual(user_save.tool_choice_embedding, "text-embedding-3-small")
        self.assertEqual(user_save.tool_choice_api_fiat_exchange, "new-fiat-api")
        self.assertEqual(user_save.tool_choice_api_crypto_exchange, "new-crypto-api")
        self.assertEqual(user_save.tool_choice_api_twitter, "new-twitter-api")

        # Check that non-updated fields remain the same
        self.assertEqual(user_save.id, self.user.id)
        self.assertEqual(user_save.full_name, self.user.full_name)
        self.assertEqual(user_save.telegram_username, self.user.telegram_username)

    def test_api_to_domain_with_partial_fields(self):
        payload = UserSettingsPayload(
            open_ai_key = "sk-new123",
            tool_choice_chat = "gpt-4o-mini",
        )

        user_save = api_to_domain(payload, self.user)

        # Check that provided fields were updated
        self.assertEqual(user_save.open_ai_key.get_secret_value() if user_save.open_ai_key else None, "sk-new123")
        self.assertEqual(user_save.tool_choice_chat, "gpt-4o-mini")

        # Check that non-provided fields remain unchanged
        self.assertEqual(user_save.anthropic_key, self.user.anthropic_key)
        self.assertEqual(user_save.google_ai_key, self.user.google_ai_key)
        self.assertEqual(user_save.tool_choice_reasoning, self.user.tool_choice_reasoning)

    def test_api_to_domain_with_empty_strings(self):
        payload = UserSettingsPayload(
            open_ai_key = "   ",  # whitespace only
            tool_choice_chat = "",  # empty string
        )

        user_save = api_to_domain(payload, self.user)

        # Check that empty/whitespace strings become None
        self.assertIsNone(user_save.open_ai_key)
        self.assertIsNone(user_save.tool_choice_chat)

    def test_domain_to_api_conversion(self):
        masked_user = domain_to_api(self.user)

        # Check basic fields
        self.assertEqual(masked_user.id, self.user.id.hex)
        self.assertEqual(masked_user.full_name, self.user.full_name)
        self.assertEqual(masked_user.telegram_username, self.user.telegram_username)
        self.assertEqual(masked_user.telegram_chat_id, self.user.telegram_chat_id)
        self.assertEqual(masked_user.telegram_user_id, self.user.telegram_user_id)
        self.assertEqual(masked_user.group, self.user.group.value)
        self.assertEqual(masked_user.created_at, self.user.created_at.isoformat())

        # Check that API keys are masked
        self.assertEqual(masked_user.open_ai_key, mask_secret(self.user.open_ai_key))
        self.assertEqual(masked_user.anthropic_key, mask_secret(self.user.anthropic_key))
        self.assertEqual(masked_user.google_ai_key, mask_secret(self.user.google_ai_key))
        self.assertEqual(masked_user.perplexity_key, mask_secret(self.user.perplexity_key))
        self.assertEqual(masked_user.replicate_key, mask_secret(self.user.replicate_key))
        self.assertEqual(masked_user.rapid_api_key, mask_secret(self.user.rapid_api_key))
        self.assertEqual(masked_user.coinmarketcap_key, mask_secret(self.user.coinmarketcap_key))

        # Check that tool choices are not masked
        self.assertEqual(masked_user.tool_choice_chat, self.user.tool_choice_chat)
        self.assertEqual(masked_user.tool_choice_reasoning, self.user.tool_choice_reasoning)
        self.assertEqual(masked_user.tool_choice_copywriting, self.user.tool_choice_copywriting)
        self.assertEqual(masked_user.tool_choice_vision, self.user.tool_choice_vision)
        self.assertEqual(masked_user.tool_choice_hearing, self.user.tool_choice_hearing)
        self.assertEqual(masked_user.tool_choice_images_gen, self.user.tool_choice_images_gen)
        self.assertEqual(masked_user.tool_choice_images_edit, self.user.tool_choice_images_edit)
        self.assertEqual(masked_user.tool_choice_images_restoration, self.user.tool_choice_images_restoration)
        self.assertEqual(masked_user.tool_choice_images_inpainting, self.user.tool_choice_images_inpainting)
        self.assertEqual(masked_user.tool_choice_images_background_removal, self.user.tool_choice_images_background_removal)
        self.assertEqual(masked_user.tool_choice_search, self.user.tool_choice_search)
        self.assertEqual(masked_user.tool_choice_embedding, self.user.tool_choice_embedding)
        self.assertEqual(masked_user.tool_choice_api_fiat_exchange, self.user.tool_choice_api_fiat_exchange)
        self.assertEqual(masked_user.tool_choice_api_crypto_exchange, self.user.tool_choice_api_crypto_exchange)
        self.assertEqual(masked_user.tool_choice_api_twitter, self.user.tool_choice_api_twitter)

    def test_domain_to_api_with_none_values(self):
        user_with_nones = self.user.model_copy(
            update = {
                "open_ai_key": None,
                "tool_choice_chat": None,
                "tool_choice_reasoning": None,
            },
        )

        masked_user = domain_to_api(user_with_nones)

        # Check that None values remain None
        self.assertIsNone(masked_user.open_ai_key)
        self.assertIsNone(masked_user.tool_choice_chat)
        self.assertIsNone(masked_user.tool_choice_reasoning)

        # Check that non-None values are still processed
        self.assertIsNotNone(masked_user.anthropic_key)
        self.assertEqual(masked_user.tool_choice_copywriting, self.user.tool_choice_copywriting)
