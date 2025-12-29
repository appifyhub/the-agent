import unittest
from io import BytesIO
from typing import IO

from features.external_tools.external_tool_library import (
    IMAGE_EDITING_FLUX_KONTEXT_PRO,
    IMAGE_GENERATION_FLUX_1_1,
)
from features.images import image_api_utils


class ImageApiUtilsTest(unittest.TestCase):

    def test_resolve_aspect_ratio_none_for_generation(self):
        result = image_api_utils.resolve_aspect_ratio(IMAGE_GENERATION_FLUX_1_1, None)
        self.assertEqual(result, "2:3")

    def test_resolve_aspect_ratio_none_for_editing_with_files(self):
        input_files: list[IO[bytes]] = [BytesIO(b"fake_image")]
        result = image_api_utils.resolve_aspect_ratio(IMAGE_EDITING_FLUX_KONTEXT_PRO, None, input_files)
        self.assertEqual(result, "match_input_image")

    def test_resolve_aspect_ratio_none_for_editing_without_files(self):
        result = image_api_utils.resolve_aspect_ratio(IMAGE_EDITING_FLUX_KONTEXT_PRO, None)
        self.assertEqual(result, "2:3")

    def test_resolve_aspect_ratio_valid_ratio(self):
        result = image_api_utils.resolve_aspect_ratio(IMAGE_GENERATION_FLUX_1_1, "1:1")
        self.assertEqual(result, "1:1")

    def test_resolve_aspect_ratio_valid_ratio_portrait(self):
        result = image_api_utils.resolve_aspect_ratio(IMAGE_GENERATION_FLUX_1_1, "2:3")
        self.assertEqual(result, "2:3")

    def test_resolve_aspect_ratio_16_9(self):
        result = image_api_utils.resolve_aspect_ratio(IMAGE_GENERATION_FLUX_1_1, "16:9")
        self.assertEqual(result, "16:9")

    def test_resolve_aspect_ratio_match_input_image_with_editing_tool_and_files(self):
        input_files: list[IO[bytes]] = [BytesIO(b"fake_image")]
        result = image_api_utils.resolve_aspect_ratio(IMAGE_EDITING_FLUX_KONTEXT_PRO, "match_input_image", input_files)
        self.assertEqual(result, "match_input_image")

    def test_resolve_aspect_ratio_match_input_image_without_files_falls_back(self):
        result = image_api_utils.resolve_aspect_ratio(IMAGE_EDITING_FLUX_KONTEXT_PRO, "match_input_image")
        self.assertEqual(result, "2:3")

    def test_resolve_aspect_ratio_match_input_image_for_generation_falls_back(self):
        result = image_api_utils.resolve_aspect_ratio(IMAGE_GENERATION_FLUX_1_1, "match_input_image")
        self.assertEqual(result, "2:3")

    def test_resolve_aspect_ratio_with_spaces(self):
        result = image_api_utils.resolve_aspect_ratio(IMAGE_GENERATION_FLUX_1_1, "2 : 3")
        self.assertEqual(result, "2:3")

    def test_resolve_aspect_ratio_with_multiple_spaces(self):
        result = image_api_utils.resolve_aspect_ratio(IMAGE_GENERATION_FLUX_1_1, "  1  :  1  ")
        self.assertEqual(result, "1:1")

    def test_resolve_aspect_ratio_with_tabs(self):
        result = image_api_utils.resolve_aspect_ratio(IMAGE_GENERATION_FLUX_1_1, "1\t:\t1")
        self.assertEqual(result, "1:1")

    def test_resolve_aspect_ratio_closest_match_slightly_off(self):
        result = image_api_utils.resolve_aspect_ratio(IMAGE_GENERATION_FLUX_1_1, "2.1:3")
        self.assertEqual(result, "2:3")

    def test_resolve_aspect_ratio_closest_match_between_two(self):
        result = image_api_utils.resolve_aspect_ratio(IMAGE_GENERATION_FLUX_1_1, "3.5:4")
        self.assertIn(result, ["3:4", "1:1"])

    def test_resolve_aspect_ratio_closest_match_landscape(self):
        result = image_api_utils.resolve_aspect_ratio(IMAGE_GENERATION_FLUX_1_1, "3.8:2")
        self.assertEqual(result, "16:9")

    def test_resolve_aspect_ratio_invalid_format_no_colon(self):
        result = image_api_utils.resolve_aspect_ratio(IMAGE_GENERATION_FLUX_1_1, "2x3")
        self.assertEqual(result, "2:3")

    def test_resolve_aspect_ratio_invalid_format_multiple_colons(self):
        result = image_api_utils.resolve_aspect_ratio(IMAGE_GENERATION_FLUX_1_1, "2:3:4")
        self.assertEqual(result, "2:3")

    def test_resolve_aspect_ratio_invalid_non_numeric(self):
        result = image_api_utils.resolve_aspect_ratio(IMAGE_GENERATION_FLUX_1_1, "a:b")
        self.assertEqual(result, "2:3")

    def test_resolve_aspect_ratio_zero_division(self):
        result = image_api_utils.resolve_aspect_ratio(IMAGE_GENERATION_FLUX_1_1, "2:0")
        self.assertEqual(result, "2:3")

    def test_resolve_aspect_ratio_invalid_for_editing_with_files(self):
        input_files: list[IO[bytes]] = [BytesIO(b"fake_image")]
        result = image_api_utils.resolve_aspect_ratio(IMAGE_EDITING_FLUX_KONTEXT_PRO, "invalid", input_files)
        self.assertEqual(result, "match_input_image")

    def test_convert_size_to_mp_from_k(self):
        self.assertEqual(image_api_utils.convert_size_to_mp("1K"), "1 MP")
        self.assertEqual(image_api_utils.convert_size_to_mp("2K"), "2 MP")
        self.assertEqual(image_api_utils.convert_size_to_mp("4K"), "4 MP")

    def test_convert_size_to_mp_already_mp(self):
        self.assertEqual(image_api_utils.convert_size_to_mp("2 MP"), "2 MP")

    def test_convert_size_to_mp_case_insensitive(self):
        self.assertEqual(image_api_utils.convert_size_to_mp("2k"), "2 MP")
        self.assertEqual(image_api_utils.convert_size_to_mp("4K"), "4 MP")

    def test_convert_size_to_mp_invalid_defaults_to_2mp(self):
        self.assertEqual(image_api_utils.convert_size_to_mp("invalid"), "2 MP")

    def test_convert_size_to_k_from_mp(self):
        self.assertEqual(image_api_utils.convert_size_to_k("1 MP"), "1K")
        self.assertEqual(image_api_utils.convert_size_to_k("2 MP"), "2K")
        self.assertEqual(image_api_utils.convert_size_to_k("4 MP"), "4K")

    def test_convert_size_to_k_already_k(self):
        self.assertEqual(image_api_utils.convert_size_to_k("2K"), "2K")

    def test_convert_size_to_k_case_insensitive(self):
        self.assertEqual(image_api_utils.convert_size_to_k("2 mp"), "2K")
        self.assertEqual(image_api_utils.convert_size_to_k("4k"), "4K")

    def test_convert_size_to_k_invalid_defaults_to_2k(self):
        self.assertEqual(image_api_utils.convert_size_to_k("invalid"), "2K")

    def test_map_to_model_parameters_preserves_file_objects(self):
        file1 = BytesIO(b"test image data")
        file2 = BytesIO(b"test image data 2")
        input_files: list[IO[bytes]] = [file1, file2]

        result = image_api_utils.map_to_model_parameters(
            tool = IMAGE_EDITING_FLUX_KONTEXT_PRO,
            prompt = "test prompt",
            aspect_ratio = "1:1",
            size = "2K",
            input_files = input_files,
        )

        self.assertIsInstance(result.image, BytesIO)
        self.assertIsInstance(result.input_image, BytesIO)
        assert result.image_input is not None
        assert result.input_images is not None
        self.assertEqual(len(result.image_input), 2)
        self.assertEqual(len(result.input_images), 2)
        self.assertIsInstance(result.image_input[0], BytesIO)
        self.assertIsInstance(result.input_images[0], BytesIO)
