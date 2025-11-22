import unittest

from features.images.aspect_ratio_utils import validate_aspect_ratio


class AspectRatioUtilsTest(unittest.TestCase):

    def test_validate_aspect_ratio_none_input(self):
        result = validate_aspect_ratio(None, "2:3")
        self.assertEqual(result, "2:3")

    def test_validate_aspect_ratio_empty_string(self):
        result = validate_aspect_ratio("", "2:3")
        self.assertEqual(result, "2:3")

    def test_validate_aspect_ratio_valid_ratio(self):
        result = validate_aspect_ratio("1:1", "2:3")
        self.assertEqual(result, "1:1")

    def test_validate_aspect_ratio_valid_ratio_portrait(self):
        result = validate_aspect_ratio("2:3", "1:1")
        self.assertEqual(result, "2:3")

    def test_validate_aspect_ratio_match_input_image_as_input_when_default(self):
        result = validate_aspect_ratio("match_input_image", "match_input_image")
        self.assertEqual(result, "match_input_image")

    def test_validate_aspect_ratio_with_spaces(self):
        result = validate_aspect_ratio("2 : 3", "1:1")
        self.assertEqual(result, "2:3")

    def test_validate_aspect_ratio_with_multiple_spaces(self):
        result = validate_aspect_ratio("  1  :  1  ", "2:3")
        self.assertEqual(result, "1:1")

    def test_validate_aspect_ratio_with_tabs(self):
        result = validate_aspect_ratio("1\t:\t1", "2:3")
        self.assertEqual(result, "1:1")

    def test_validate_aspect_ratio_closest_match_slightly_off(self):
        # 2.1:3 = 0.7, closest to 2:3 = 0.667
        result = validate_aspect_ratio("2.1:3", "1:1")
        self.assertEqual(result, "2:3")

    def test_validate_aspect_ratio_closest_match_between_two(self):
        # 3.5:4 = 0.875, between 3:4 (0.75) and 1:1 (1.0)
        # Distance to 3:4 = 0.125, distance to 1:1 = 0.125 (tie, min picks first in list order)
        result = validate_aspect_ratio("3.5:4", "2:3")
        # Should pick 1:1 or 3:4, both equidistant at 0.125
        self.assertIn(result, ["3:4", "1:1"])

    def test_validate_aspect_ratio_closest_match_landscape(self):
        # 3.8:2 = 1.9, closest to 16:9 = 1.778
        result = validate_aspect_ratio("3.8:2", "1:1")
        self.assertEqual(result, "16:9")

    def test_validate_aspect_ratio_invalid_format_no_colon(self):
        result = validate_aspect_ratio("2x3", "2:3")
        self.assertEqual(result, "2:3")

    def test_validate_aspect_ratio_invalid_format_multiple_colons(self):
        result = validate_aspect_ratio("2:3:4", "1:1")
        self.assertEqual(result, "1:1")

    def test_validate_aspect_ratio_invalid_non_numeric(self):
        result = validate_aspect_ratio("a:b", "2:3")
        self.assertEqual(result, "2:3")

    def test_validate_aspect_ratio_zero_division(self):
        result = validate_aspect_ratio("2:0", "2:3")
        self.assertEqual(result, "2:3")

    def test_validate_aspect_ratio_match_input_image_as_default(self):
        result = validate_aspect_ratio(None, "match_input_image")
        self.assertEqual(result, "match_input_image")

    def test_validate_aspect_ratio_invalid_matches_default_when_default_is_special(self):
        result = validate_aspect_ratio("invalid", "match_input_image")
        self.assertEqual(result, "match_input_image")
