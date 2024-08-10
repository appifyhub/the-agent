import unittest

from features.prompting.prompt_builder import PromptBuilder, PromptSection


class PromptBuilderTest(unittest.TestCase):

    def test_init_with_content(self):
        initial = "Initial prompt"
        builder = PromptBuilder(initial)
        self.assertEqual(builder.build(), initial)

    def test_init_no_content(self):
        builder = PromptBuilder()
        self.assertEqual(builder.build(), "")

    def test_add_single_section(self):
        builder = PromptBuilder()
        result = builder.add_section(PromptSection.style, "Write in a formal style").build()
        expected = f"[Style]\nWrite in a formal style"
        self.assertEqual(result, expected)

    def test_add_multiple_sections(self):
        builder = PromptBuilder()
        result = (
            builder
            .add_section(PromptSection.style, "Write in a formal style")
            .add_section(PromptSection.tone, "Use a professional tone")
            .add_section(PromptSection.context, "You are writing a business report")
            .build()
        )
        expected = (
            "[Style]\nWrite in a formal style\n\n"
            "[Tone]\nUse a professional tone\n\n"
            "[Context]\nYou are writing a business report"
        )
        self.assertEqual(result, expected)

    def test_all_prompt_sections(self):
        builder = PromptBuilder("Initial prompt")
        for section in PromptSection:
            builder = builder.add_section(section, f"Content for {section.value}")
        result = builder.build()
        expected = (
            "Initial prompt\n\n"
            "[Style]\nContent for Style\n\n"
            "[Format]\nContent for Format\n\n"
            "[Context]\nContent for Context\n\n"
            "[Tone]\nContent for Tone\n\n"
            "[Quirks]\nContent for Quirks\n\n"
            "[Appendix]\nContent for Appendix\n\n"
            "[Important Reminder]\nContent for Important Reminder\n\n"
            "[Metadata]\nContent for Metadata"
        )
        self.assertEqual(result, expected)

    def test_appending_builder(self):
        initial = PromptBuilder("Initial prompt").add_section(PromptSection.style, "Write in a formal style")
        additional = PromptBuilder("Additional prompt").add_section(PromptSection.tone, "Use a professional tone")
        result = initial.append(additional).build()
        expected = (
            "Initial prompt\n\n"
            "[Style]\nWrite in a formal style\n\n"
            "Additional prompt\n\n"
            "[Tone]\nUse a professional tone"
        )
        self.assertEqual(result, expected)
