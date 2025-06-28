import unittest

from api.models.user_settings_payload import UserSettingsPayload


class UserSettingsPayloadTest(unittest.TestCase):

    def test_basic_creation_with_all_fields(self):
        """Test creating payload with all fields provided"""
        payload = UserSettingsPayload(
            open_ai_key = "sk-abc123",
            anthropic_key = "sk-ant-def456",
            perplexity_key = "pplx-ghi789",
            replicate_key = "r8_jkl012",
            rapid_api_key = "mno345",
            coinmarketcap_key = "pqr678-stu-901",
        )

        self.assertEqual(payload.open_ai_key, "sk-abc123")
        self.assertEqual(payload.anthropic_key, "sk-ant-def456")
        self.assertEqual(payload.perplexity_key, "pplx-ghi789")
        self.assertEqual(payload.replicate_key, "r8_jkl012")
        self.assertEqual(payload.rapid_api_key, "mno345")
        self.assertEqual(payload.coinmarketcap_key, "pqr678-stu-901")

    def test_partial_creation_with_some_fields(self):
        """Test creating payload with only some fields provided"""
        payload = UserSettingsPayload(
            open_ai_key = "sk-abc123",
            anthropic_key = "sk-ant-def456",
        )

        self.assertEqual(payload.open_ai_key, "sk-abc123")
        self.assertEqual(payload.anthropic_key, "sk-ant-def456")
        self.assertIsNone(payload.perplexity_key)
        self.assertIsNone(payload.replicate_key)
        self.assertIsNone(payload.rapid_api_key)
        self.assertIsNone(payload.coinmarketcap_key)

    def test_string_trimming_validation(self):
        """Test that string fields are properly trimmed"""
        payload = UserSettingsPayload(
            open_ai_key = "  sk-abc123  ",
            anthropic_key = "\tsk-ant-def456\n",
            perplexity_key = " pplx-ghi789 ",
        )

        self.assertEqual(payload.open_ai_key, "sk-abc123")
        self.assertEqual(payload.anthropic_key, "sk-ant-def456")
        self.assertEqual(payload.perplexity_key, "pplx-ghi789")

    def test_empty_strings_after_trimming(self):
        """Test that empty strings after trimming remain empty strings"""
        payload = UserSettingsPayload(
            open_ai_key = "   ",  # Spaces only
            anthropic_key = "\t\n",  # Tabs and newlines
            perplexity_key = "",  # Already empty
        )

        # After trimming, these should all be empty strings
        self.assertEqual(payload.open_ai_key, "")
        self.assertEqual(payload.anthropic_key, "")
        self.assertEqual(payload.perplexity_key, "")

    def test_none_values_preserved(self):
        """Test that None values are preserved and not converted"""
        payload = UserSettingsPayload(
            open_ai_key = None,
            anthropic_key = "sk-ant-123",
        )

        self.assertIsNone(payload.open_ai_key)
        self.assertEqual(payload.anthropic_key, "sk-ant-123")

    def test_empty_payload(self):
        """Test creating an empty payload (all defaults)"""
        payload = UserSettingsPayload()

        self.assertIsNone(payload.open_ai_key)
        self.assertIsNone(payload.anthropic_key)
        self.assertIsNone(payload.perplexity_key)
        self.assertIsNone(payload.replicate_key)
        self.assertIsNone(payload.rapid_api_key)
        self.assertIsNone(payload.coinmarketcap_key)
