import unittest

from pydantic import ValidationError

from api.model.chat_settings_payload import ChatSettingsPayload


class ChatSettingsPayloadTest(unittest.TestCase):

    def test_basic_creation_with_all_fields(self):
        """Test creating payload with all fields provided"""
        payload = ChatSettingsPayload(
            language_name = "Spanish",
            language_iso_code = "es",
            reply_chance_percent = 75,
            release_notifications = "all",
        )

        self.assertEqual(payload.language_name, "Spanish")
        self.assertEqual(payload.language_iso_code, "es")
        self.assertEqual(payload.reply_chance_percent, 75)
        self.assertEqual(payload.release_notifications, "all")

    def test_missing_required_fields_raises_error(self):
        """Test that missing required fields raise ValidationError"""
        # Test empty payload raises ValidationError
        with self.assertRaises(ValidationError):
            ChatSettingsPayload(**{})

    def test_string_trimming_validation(self):
        """Test that string fields are properly trimmed"""
        payload = ChatSettingsPayload(
            language_name = "  English  ",
            language_iso_code = "\ten\n",
            reply_chance_percent = 50,
            release_notifications = "  none  ",
        )

        self.assertEqual(payload.language_name, "English")
        self.assertEqual(payload.language_iso_code, "en")
        self.assertEqual(payload.reply_chance_percent, 50)
        self.assertEqual(payload.release_notifications, "none")

    def test_empty_strings_after_trimming(self):
        """Test that empty strings after trimming remain empty strings"""
        payload = ChatSettingsPayload(
            language_name = "   ",  # Spaces only
            language_iso_code = "",  # Already empty
            reply_chance_percent = 25,
            release_notifications = "\t\n",  # Tabs and newlines
        )

        # After trimming, these should all be empty strings
        self.assertEqual(payload.language_name, "")
        self.assertEqual(payload.language_iso_code, "")
        self.assertEqual(payload.reply_chance_percent, 25)
        self.assertEqual(payload.release_notifications, "")

    def test_reply_chance_validation_valid_values(self):
        """Test that valid reply chance percentages are accepted"""
        # Test boundary values
        payload_0 = ChatSettingsPayload(
            language_name = "English",
            language_iso_code = "en",
            reply_chance_percent = 0,
            release_notifications = "all",
        )
        payload_100 = ChatSettingsPayload(
            language_name = "English",
            language_iso_code = "en",
            reply_chance_percent = 100,
            release_notifications = "all",
        )
        payload_50 = ChatSettingsPayload(
            language_name = "English",
            language_iso_code = "en",
            reply_chance_percent = 50,
            release_notifications = "all",
        )

        self.assertEqual(payload_0.reply_chance_percent, 0)
        self.assertEqual(payload_100.reply_chance_percent, 100)
        self.assertEqual(payload_50.reply_chance_percent, 50)

    def test_reply_chance_validation_invalid_values(self):
        """Test that invalid reply chance percentages are rejected"""
        # Test values outside valid range
        with self.assertRaises(ValidationError) as context:
            ChatSettingsPayload(
                language_name = "English",
                language_iso_code = "en",
                reply_chance_percent = -1,
                release_notifications = "all",
            )
        self.assertIn("Reply chance percent must be between 0 and 100", str(context.exception))

        with self.assertRaises(ValidationError) as context:
            ChatSettingsPayload(
                language_name = "English",
                language_iso_code = "en",
                reply_chance_percent = 101,
                release_notifications = "all",
            )
        self.assertIn("Reply chance percent must be between 0 and 100", str(context.exception))
