import unittest
from unittest.mock import MagicMock, patch

from features.stable_diffusion_image_generator import (
    StableDiffusionImageGenerator,
    BASIC_MODEL,
    ADVANCED_MODEL,
)


class StableDiffusionImageGeneratorTest(unittest.TestCase):

    def setUp(self):
        self.prompt = "test prompt"
        self.replicate_api_key = "test_key"

    def test_init(self):
        generator = StableDiffusionImageGenerator(
            self.prompt,
            False,
            self.replicate_api_key,
        )
        self.assertIsInstance(generator, StableDiffusionImageGenerator)

    @patch("features.stable_diffusion_image_generator.replicate.Client")
    def test_execute_basic_model(self, mock_client):
        mock_run = MagicMock(return_value = ["http://example.com/image.png"])
        mock_client.return_value.run = mock_run

        generator = StableDiffusionImageGenerator(
            self.prompt,
            False,
            self.replicate_api_key,
        )
        result = generator.execute()

        self.assertEqual(result, "http://example.com/image.png")
        mock_run.assert_called_once_with(
            BASIC_MODEL,
            input = {
                "prompt": self.prompt,
                "aspect_ratio": "3:2",
                "output_format": "png",
                "output_quality": 100,
                "num_inference_steps": 25,
                "num_outputs": 1,
            }
        )

    @patch("features.stable_diffusion_image_generator.replicate.Client")
    def test_execute_advanced_model(self, mock_client):
        mock_run = MagicMock(return_value = ["http://example.com/image.png"])
        mock_client.return_value.run = mock_run

        generator = StableDiffusionImageGenerator(
            self.prompt,
            True,
            self.replicate_api_key,
        )
        result = generator.execute()

        self.assertEqual(result, "http://example.com/image.png")
        mock_run.assert_called_once_with(
            ADVANCED_MODEL,
            input = {
                "prompt": self.prompt,
                "aspect_ratio": "3:2",
                "output_format": "png",
                "output_quality": 100,
                "num_inference_steps": 25,
                "num_outputs": 1,
            }
        )

    @patch("features.stable_diffusion_image_generator.replicate.Client")
    def test_execute_failure(self, mock_client):
        mock_client.return_value.run.side_effect = Exception("API error")

        generator = StableDiffusionImageGenerator(
            self.prompt,
            False,
            self.replicate_api_key,
        )
        result = generator.execute()

        self.assertIsNone(result)

    @patch("features.stable_diffusion_image_generator.replicate.Client")
    def test_execute_empty_result(self, mock_client):
        mock_client.return_value.run.return_value = []

        generator = StableDiffusionImageGenerator(
            self.prompt,
            False,
            self.replicate_api_key,
        )
        result = generator.execute()

        self.assertIsNone(result)
