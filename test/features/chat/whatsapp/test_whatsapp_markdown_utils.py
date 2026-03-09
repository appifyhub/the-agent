import unittest

from features.chat.whatsapp.whatsapp_markdown_utils import convert_for_whatsapp


class WhatsAppMarkdownUtilsTest(unittest.TestCase):

    def test_convert_double_bold_to_single(self):
        self.assertEqual(convert_for_whatsapp("**bold**"), "*bold*")
        self.assertEqual(convert_for_whatsapp("**bold text**"), "*bold text*")

    def test_convert_double_bold_adjacent_to_punctuation(self):
        self.assertEqual(convert_for_whatsapp("**bold**,"), "*bold*,")
        self.assertEqual(convert_for_whatsapp("**bold**."), "*bold*.")
        self.assertEqual(convert_for_whatsapp("**bold.**"), "*bold.*")
        self.assertEqual(convert_for_whatsapp("**bold**!"), "*bold*!")
        self.assertEqual(convert_for_whatsapp("**bold**?"), "*bold*?")
        self.assertEqual(convert_for_whatsapp("Text: **bold**."), "Text: *bold*.")

    def test_preserves_single_asterisk_bold(self):
        # WhatsApp native single-asterisk bold should remain unchanged
        self.assertEqual(convert_for_whatsapp("*bold*"), "*bold*")
        self.assertEqual(convert_for_whatsapp("*bold text*"), "*bold text*")

    def test_preserves_inline_code(self):
        self.assertEqual(convert_for_whatsapp("`code`"), "`code`")
        self.assertEqual(convert_for_whatsapp("Use `my_func()` here"), "Use `my_func()` here")

    def test_preserves_code_blocks(self):
        text = "Example:\n```python\nmy_var = 42\n```\nDone"
        self.assertEqual(convert_for_whatsapp(text), text)

    def test_does_not_convert_bold_inside_code_blocks(self):
        text = "```\n**not bold**\n```"
        self.assertEqual(convert_for_whatsapp(text), text)

    def test_does_not_convert_bold_inside_inline_code(self):
        text = "`**not bold**`"
        self.assertEqual(convert_for_whatsapp(text), text)

    def test_convert_multiple_bold_segments(self):
        text = "**Hello** and **world**!"
        expected = "*Hello* and *world*!"
        self.assertEqual(convert_for_whatsapp(text), expected)

    def test_empty_string(self):
        self.assertEqual(convert_for_whatsapp(""), "")

    def test_no_formatting(self):
        text = "Plain text without formatting."
        self.assertEqual(convert_for_whatsapp(text), text)

    def test_real_world_release_title(self):
        text = "**🚀 Verzija 5.0.6: Čišći Digitalni Otisak**"
        expected = "*🚀 Verzija 5.0.6: Čišći Digitalni Otisak*"
        self.assertEqual(convert_for_whatsapp(text), expected)
