import unittest
from dataclasses import fields

from features.external_tools.external_tool import ToolType
from features.external_tools.intelligence_presets import (
    INTELLIGENCE_PRESETS,
    IntelligencePreset,
    PresetChoices,
    get_all_presets,
)


class IntelligencePresetsTest(unittest.TestCase):

    def test_preset_choices_covers_all_tool_types(self):
        preset_field_names = {f.name for f in fields(PresetChoices)}
        tool_type_names = {t.value for t in ToolType}
        self.assertEqual(
            preset_field_names,
            tool_type_names,
            f"PresetChoices fields {preset_field_names} should match ToolTypes {tool_type_names}",
        )

    def test_all_presets_exist(self):
        self.assertIn(IntelligencePreset.lowest_price, INTELLIGENCE_PRESETS)
        self.assertIn(IntelligencePreset.highest_price, INTELLIGENCE_PRESETS)
        self.assertIn(IntelligencePreset.agent_choice, INTELLIGENCE_PRESETS)

    def test_preset_choices_as_dict_filters_none(self):
        choices = PresetChoices(chat = "test-chat", reasoning = None)
        result = choices.as_dict()
        self.assertIn(ToolType.chat.value, result)
        self.assertNotIn(ToolType.reasoning.value, result)
        self.assertEqual(result[ToolType.chat.value], "test-chat")

    def test_preset_choices_as_dict_uses_tool_type_values(self):
        choices = PresetChoices(
            chat = "chat-model",
            vision = "vision-model",
            embedding = "embed-model",
        )
        result = choices.as_dict()
        self.assertEqual(result["chat"], "chat-model")
        self.assertEqual(result["vision"], "vision-model")
        self.assertEqual(result["embedding"], "embed-model")

    def test_get_all_presets_returns_dict_with_all_presets(self):
        result = get_all_presets()
        self.assertIsInstance(result, dict)
        self.assertIn("lowest_price", result)
        self.assertIn("highest_price", result)
        self.assertIn("agent_choice", result)

    def test_get_all_presets_values_are_dicts(self):
        result = get_all_presets()
        for preset_name, choices in result.items():
            self.assertIsInstance(choices, dict, f"Preset {preset_name} should be a dict")
            for tool_type, tool_id in choices.items():
                self.assertIsInstance(tool_type, str)
                self.assertIsInstance(tool_id, str)

    def test_all_presets_have_required_tool_types(self):
        required_types = ["chat", "reasoning", "vision", "hearing", "search", "embedding"]
        result = get_all_presets()
        for preset_name, choices in result.items():
            for tool_type in required_types:
                self.assertIn(
                    tool_type,
                    choices,
                    f"Preset {preset_name} missing required tool type {tool_type}",
                )

    def test_preset_tool_ids_are_non_empty(self):
        result = get_all_presets()
        for preset_name, choices in result.items():
            for tool_type, tool_id in choices.items():
                self.assertTrue(
                    len(tool_id) > 0,
                    f"Preset {preset_name} has empty tool_id for {tool_type}",
                )
