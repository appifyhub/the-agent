import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

from langchain_core.messages import AIMessage

from db.crud.user import UserCRUD
from db.model.user import UserDB
from db.schema.user import User
from features.chat.telegram.telegram_bot_api import TelegramBotAPI
from features.images.generative_imaging_manager import GenerativeImagingManager
from features.images.stable_diffusion_image_generator import StableDiffusionImageGenerator


class GenerativeImagingManagerTest(unittest.TestCase):
    chat_id: str
    raw_prompt: str
    invoker_user_id_hex: str
    user: User
    mock_bot_api: MagicMock
    mock_user_dao: MagicMock

    def setUp(self):
        self.chat_id = "test_chat_id"
        self.raw_prompt = "Generate a beautiful landscape"
        self.invoker_user_id_hex = "123e4567-e89b-12d3-a456-426614174000"
        self.user = User(
            id = UUID(hex = self.invoker_user_id_hex),
            full_name = "Test User",
            telegram_username = "test_username",
            telegram_chat_id = "test_chat_id",
            telegram_user_id = 1,
            open_ai_key = "test_api_key",
            group = UserDB.Group.alpha,
            created_at = datetime.now().date(),
        )
        self.mock_bot_api = MagicMock(spec = TelegramBotAPI)
        self.mock_user_dao = MagicMock(spec = UserCRUD)
        self.mock_user_dao.get.return_value = self.user

    def test_init_success(self):
        manager = GenerativeImagingManager(
            self.chat_id,
            self.raw_prompt,
            self.invoker_user_id_hex,
            self.mock_bot_api,
            self.mock_user_dao,
        )
        self.assertIsInstance(manager, GenerativeImagingManager)

    def test_init_user_not_found(self):
        self.mock_user_dao.get.return_value = None
        with self.assertRaises(ValueError):
            GenerativeImagingManager(
                self.chat_id,
                self.raw_prompt,
                self.invoker_user_id_hex,
                self.mock_bot_api,
                self.mock_user_dao,
            )

    def test_init_user_not_allowed(self):
        self.user.group = UserDB.Group.standard
        with self.assertRaises(ValueError):
            GenerativeImagingManager(
                self.chat_id,
                self.raw_prompt,
                self.invoker_user_id_hex,
                self.mock_bot_api,
                self.mock_user_dao,
            )

    @patch("features.images.generative_imaging_manager.ChatAnthropic")
    @patch.object(StableDiffusionImageGenerator, "execute")
    @patch.object(GenerativeImagingManager, "store_bot_photo")
    def test_execute_success_with_store_bot_photo(self, mock_store_bot_photo, mock_sd_execute, mock_chat_anthropic):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "Refined prompt")
        mock_chat_anthropic.return_value = mock_llm

        mock_sd_execute.return_value = "http://example.com/image.png"
        self.mock_bot_api.send_photo.return_value = {"result": {"message_id": 123}}

        manager = GenerativeImagingManager(
            self.chat_id,
            self.raw_prompt,
            self.invoker_user_id_hex,
            self.mock_bot_api,
            self.mock_user_dao,
        )
        result = manager.execute()

        self.assertEqual(result, GenerativeImagingManager.Result.success)
        mock_llm.invoke.assert_called_once()
        mock_sd_execute.assert_called_once()
        self.mock_bot_api.send_photo.assert_called_once_with(self.chat_id, "http://example.com/image.png")
        mock_store_bot_photo.assert_called_once_with({"result": {"message_id": 123}})

    @patch("features.images.generative_imaging_manager.TelegramDomainMapper")
    @patch("features.images.generative_imaging_manager.TelegramDataResolver")
    def test_store_bot_photo_success(self, mock_resolver_class, mock_mapper_class):
        mock_mapper = MagicMock()
        mock_mapper.map_update.return_value = {"mapped": "data"}
        mock_mapper_class.return_value = mock_mapper

        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = MagicMock(message = "test_message", attachments = ["test_attachment"])
        mock_resolver_class.return_value = mock_resolver

        # Create a mock database object
        mock_db = MagicMock()
        # Attach the mock database to the mock user_dao
        self.mock_user_dao._db = mock_db

        manager = GenerativeImagingManager(
            self.chat_id,
            self.raw_prompt,
            self.invoker_user_id_hex,
            self.mock_bot_api,
            self.mock_user_dao,
        )

        api_result = {
            "result": {
                "message_id": 123,
                "from": {"id": 12345, "is_bot": True, "first_name": "TestBot", "username": "testbot"},
                "chat": {
                    "id": 67890, "type": "private", "username": "testuser", "first_name": "Test", "last_name": "User"
                },
                "date": int(datetime.now().timestamp()),
                "photo": [{
                    "file_id": "test_file_id", "file_unique_id": "test_unique_id",
                    "file_size": 1234, "width": 100, "height": 100
                }]
            }
        }
        manager.store_bot_photo(api_result)

        mock_mapper.map_update.assert_called_once()
        mock_resolver.resolve.assert_called_once_with({"mapped": "data"})

    @patch("features.images.generative_imaging_manager.ChatAnthropic")
    def test_execute_llm_failure(self, mock_chat_anthropic):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("LLM error")
        mock_chat_anthropic.return_value = mock_llm

        manager = GenerativeImagingManager(
            self.chat_id,
            self.raw_prompt,
            self.invoker_user_id_hex,
            self.mock_bot_api,
            self.mock_user_dao,
        )
        result = manager.execute()

        self.assertEqual(result, GenerativeImagingManager.Result.failed)
        mock_llm.invoke.assert_called_once()
        self.mock_bot_api.send_photo.assert_not_called()

    @patch("features.images.generative_imaging_manager.ChatAnthropic")
    @patch.object(StableDiffusionImageGenerator, "execute")
    def test_execute_image_generation_failure(self, mock_sd_execute, mock_chat_anthropic):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "Refined prompt")
        mock_chat_anthropic.return_value = mock_llm

        mock_sd_execute.return_value = None

        manager = GenerativeImagingManager(
            self.chat_id,
            self.raw_prompt,
            self.invoker_user_id_hex,
            self.mock_bot_api,
            self.mock_user_dao,
        )
        result = manager.execute()

        self.assertEqual(result, GenerativeImagingManager.Result.failed)
        mock_llm.invoke.assert_called_once()
        mock_sd_execute.assert_called_once()
        self.mock_bot_api.send_photo.assert_not_called()

    @patch("features.images.generative_imaging_manager.ChatAnthropic")
    @patch.object(StableDiffusionImageGenerator, "execute")
    def test_execute_send_photo_failure(self, mock_sd_execute, mock_chat_anthropic):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "Refined prompt")
        mock_chat_anthropic.return_value = mock_llm

        mock_sd_execute.return_value = "http://example.com/image.png"
        self.mock_bot_api.send_photo.side_effect = Exception("Send photo error")

        manager = GenerativeImagingManager(
            self.chat_id,
            self.raw_prompt,
            self.invoker_user_id_hex,
            self.mock_bot_api,
            self.mock_user_dao,
        )
        result = manager.execute()

        self.assertEqual(result, GenerativeImagingManager.Result.failed)
        mock_llm.invoke.assert_called_once()
        mock_sd_execute.assert_called_once()
        self.mock_bot_api.send_photo.assert_called_once()

    @patch("features.images.generative_imaging_manager.ChatAnthropic")
    def test_execute_non_ai_message(self, mock_chat_anthropic):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "Not an AIMessage"
        mock_chat_anthropic.return_value = mock_llm

        manager = GenerativeImagingManager(
            self.chat_id,
            self.raw_prompt,
            self.invoker_user_id_hex,
            self.mock_bot_api,
            self.mock_user_dao,
        )
        result = manager.execute()

        self.assertEqual(result, GenerativeImagingManager.Result.failed)
        mock_llm.invoke.assert_called_once()
        self.mock_bot_api.send_photo.assert_not_called()

    def test_use_advanced_model(self):
        manager = GenerativeImagingManager(
            self.chat_id,
            self.raw_prompt,
            self.invoker_user_id_hex,
            self.mock_bot_api,
            self.mock_user_dao,
        )
        # noinspection PyUnresolvedReferences
        self.assertTrue(manager._GenerativeImagingManager__use_advanced_model)

        self.user.group = UserDB.Group.beta
        manager = GenerativeImagingManager(
            self.chat_id,
            self.raw_prompt,
            self.invoker_user_id_hex,
            self.mock_bot_api,
            self.mock_user_dao,
        )
        # noinspection PyUnresolvedReferences
        self.assertFalse(manager._GenerativeImagingManager__use_advanced_model)
