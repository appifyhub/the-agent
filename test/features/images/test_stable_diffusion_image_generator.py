import unittest
from unittest.mock import MagicMock, patch

from features.ai_tools.external_ai_tool_library import IMAGE_GENERATION_FLUX
from features.images.stable_diffusion_image_generator import StableDiffusionImageGenerator


class StableDiffusionImageGeneratorTest(unittest.TestCase):

    def setUp(self):
        self.prompt = "test prompt"
        self.replicate_api_key = "test_key"

    def test_init(self):
        generator = StableDiffusionImageGenerator(self.prompt, self.replicate_api_key)
        self.assertIsInstance(generator, StableDiffusionImageGenerator)

    @patch("features.images.stable_diffusion_image_generator.replicate.Client")
    def test_execute_success(self, mock_client):
        mock_run = MagicMock(return_value = "http://example.com/image.png")
        mock_client.return_value.run = mock_run

        generator = StableDiffusionImageGenerator(self.prompt, self.replicate_api_key)
        result = generator.execute()

        self.assertEqual(result, "http://example.com/image.png")
        mock_run.assert_called_once_with(
            IMAGE_GENERATION_FLUX.id,
            input = {
                "prompt": self.prompt,
                "prompt_upsampling": True,
                "aspect_ratio": "2:3",
                "output_format": "png",
                "output_quality": 100,
                "num_inference_steps": 30,
                "safety_tolerance": 5,
                "num_outputs": 1,
            },
        )

    @patch("features.images.stable_diffusion_image_generator.replicate.Client")
    def test_execute_failure(self, mock_client):
        mock_client.return_value.run.side_effect = Exception("API error")
        generator = StableDiffusionImageGenerator(self.prompt, self.replicate_api_key)
        result = generator.execute()
        self.assertIsNone(result)

    @patch("features.images.stable_diffusion_image_generator.replicate.Client")
    def test_execute_empty_result(self, mock_client):
        mock_client.return_value.run.return_value = ""
        generator = StableDiffusionImageGenerator(self.prompt, self.replicate_api_key)
        result = generator.execute()
        self.assertEqual(result, "")
