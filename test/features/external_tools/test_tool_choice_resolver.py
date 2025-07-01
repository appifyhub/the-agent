import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from features.external_tools.external_tool import ExternalTool, ExternalToolProvider, ToolType
from features.external_tools.tool_choice_resolver import ToolChoiceResolver, ToolChoiceResolutionError
from db.schema.sponsorship import Sponsorship
from db.schema.user import User


class TestToolChoiceResolver(unittest.TestCase):

    def setUp(self):
        self.user_id = uuid4()
        self.sponsor_id = uuid4()
        
        # Create test user
        self.test_user = User(
            id = self.user_id,
            full_name = "Test User",
            telegram_username = "testuser",
            telegram_chat_id = "123456",
            telegram_user_id = 123456,
            tool_choice_llm = "gpt-4o",
            tool_choice_vision = "claude-3-5-sonnet-latest",
            tool_choice_hearing = None,
            tool_choice_images = None,
            tool_choice_search = None,
            tool_choice_embedding = None,
            tool_choice_api = None,
            created_at = "2024-01-01",
        )
        
        # Create test sponsor
        self.test_sponsor = User(
            id = self.sponsor_id,
            full_name = "Test Sponsor",
            telegram_username = "testsponsor",
            telegram_chat_id = "789012",
            telegram_user_id = 789012,
            tool_choice_llm = "claude-3-5-sonnet-latest",
            tool_choice_vision = "gpt-4o",
            tool_choice_hearing = "whisper-1",
            tool_choice_images = "gpt-image-1",
            tool_choice_search = "sonar",
            tool_choice_embedding = "text-embedding-3-small",
            tool_choice_api = "currency-converter5.p.rapidapi.com",
            created_at = "2024-01-01",
        )
        
        # Create test external tools
        self.test_provider = ExternalToolProvider(
            id = "test-provider",
            name = "Test Provider",
            token_management_url = "https://test.com",
            token_format = "test-format",
            tools = ["Test Tool"],
        )
        
        self.gpt_4o = ExternalTool(
            id = "gpt-4o",
            name = "GPT 4o",
            provider = self.test_provider,
            types = [ToolType.llm, ToolType.vision],
        )
        
        self.claude_sonnet = ExternalTool(
            id = "claude-3-5-sonnet-latest",
            name = "Claude 3.5 Sonnet",
            provider = self.test_provider,
            types = [ToolType.llm, ToolType.vision],
        )
        
        self.whisper = ExternalTool(
            id = "whisper-1",
            name = "Whisper 1",
            provider = self.test_provider,
            types = [ToolType.hearing],
        )
        
        # Mock DAOs
        self.mock_user_dao = Mock()
        self.mock_sponsorship_dao = Mock()
        
        # Create resolver
        self.resolver = ToolChoiceResolver(
            self.test_user,
            self.mock_user_dao,
            self.mock_sponsorship_dao,
        )

    @patch("features.external_tools.tool_choice_resolver.ALL_EXTERNAL_TOOLS")
    def test_get_choice_with_direct_user_choice(self, mock_tools):
        """Test that direct user choice is returned when available."""
        mock_tools.__iter__.return_value = [self.gpt_4o, self.claude_sonnet]
        
        result = self.resolver.get_choice(ToolType.llm)
        
        self.assertEqual(result, self.gpt_4o)

    @patch("features.external_tools.tool_choice_resolver.ALL_EXTERNAL_TOOLS")
    def test_get_choice_with_preferred_tool(self, mock_tools):
        """Test that preferred tool is used when compatible."""
        mock_tools.__iter__.return_value = [self.gpt_4o, self.claude_sonnet]
        
        result = self.resolver.get_choice(ToolType.llm, self.claude_sonnet)
        
        self.assertEqual(result, self.claude_sonnet)

    @patch("features.external_tools.tool_choice_resolver.ALL_EXTERNAL_TOOLS")
    def test_get_choice_preferred_tool_incompatible(self, mock_tools):
        """Test that preferred tool is ignored if incompatible with tool type."""
        mock_tools.__iter__.return_value = [self.gpt_4o, self.claude_sonnet, self.whisper]
        
        # Try to use whisper (hearing tool) for LLM - should fallback to user choice
        result = self.resolver.get_choice(ToolType.llm, self.whisper)
        
        self.assertEqual(result, self.gpt_4o)  # Should use user's LLM choice

    @patch("features.external_tools.tool_choice_resolver.ALL_EXTERNAL_TOOLS")
    def test_get_choice_invalid_user_choice_fallback_to_sponsor(self, mock_tools):
        """Test fallback to sponsor choice when user choice is invalid."""
        mock_tools.__iter__.return_value = [self.claude_sonnet, self.whisper]
        
        # User has gpt-4o configured but it's not in available tools
        # Should fallback to sponsor choice
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = [
            Mock(sponsor_id = self.sponsor_id, receiver_id = self.user_id)
        ]
        self.mock_user_dao.get.return_value = Mock(**self.test_sponsor.model_dump())
        
        result = self.resolver.get_choice(ToolType.llm)
        
        self.assertEqual(result, self.claude_sonnet)

    @patch("features.external_tools.tool_choice_resolver.ALL_EXTERNAL_TOOLS")
    def test_get_choice_no_sponsorship_fallback_to_default(self, mock_tools):
        """Test fallback to default when no user choice and no sponsorship."""
        mock_tools.__iter__.return_value = [self.claude_sonnet, self.whisper]
        
        # User has no choice for hearing, no sponsorship
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []
        
        result = self.resolver.get_choice(ToolType.hearing)
        
        self.assertEqual(result, self.whisper)  # First tool that supports hearing

    @patch("features.external_tools.tool_choice_resolver.ALL_EXTERNAL_TOOLS")
    def test_get_choice_no_tools_available(self, mock_tools):
        """Test that None is returned when no tools are available for type."""
        mock_tools.__iter__.return_value = [self.gpt_4o]  # Only LLM tools available
        
        result = self.resolver.get_choice(ToolType.hearing)
        
        self.assertIsNone(result)

    @patch("features.external_tools.tool_choice_resolver.ALL_EXTERNAL_TOOLS")
    def test_require_choice_success(self, mock_tools):
        """Test that require_choice returns tool when available."""
        mock_tools.__iter__.return_value = [self.gpt_4o, self.claude_sonnet]
        
        result = self.resolver.require_choice(ToolType.llm)
        
        self.assertEqual(result, self.gpt_4o)

    @patch("features.external_tools.tool_choice_resolver.ALL_EXTERNAL_TOOLS")
    def test_require_choice_raises_error_when_none_available(self, mock_tools):
        """Test that require_choice raises exception when no tool is available."""
        mock_tools.__iter__.return_value = [self.gpt_4o]  # Only LLM tools available
        
        with self.assertRaises(ToolChoiceResolutionError) as context:
            self.resolver.require_choice(ToolType.hearing)
        
        self.assertIn("hearing", str(context.exception))

    @patch("features.external_tools.tool_choice_resolver.ALL_EXTERNAL_TOOLS")
    def test_require_choice_raises_error_with_preferred_tool(self, mock_tools):
        """Test that require_choice includes preferred tool in error message."""
        mock_tools.__iter__.return_value = []  # No tools available
        
        with self.assertRaises(ToolChoiceResolutionError) as context:
            self.resolver.require_choice(ToolType.llm, self.gpt_4o)
        
        error_message = str(context.exception)
        self.assertIn("llm", error_message)
        self.assertIn("GPT 4o", error_message)

    @patch("features.external_tools.tool_choice_resolver.ALL_EXTERNAL_TOOLS")
    def test_user_choice_mapping_through_public_interface(self, mock_tools):
        """Test that user choices are correctly used through the public interface."""
        mock_tools.__iter__.return_value = [self.gpt_4o, self.claude_sonnet, self.whisper]
        
        # Test LLM choice
        llm_result = self.resolver.get_choice(ToolType.llm)
        self.assertEqual(llm_result, self.gpt_4o)
        
        # Test vision choice
        vision_result = self.resolver.get_choice(ToolType.vision)
        self.assertEqual(vision_result, self.claude_sonnet)
        
        # Test hearing choice (should fallback to default since user has no choice)
        hearing_result = self.resolver.get_choice(ToolType.hearing)
        self.assertEqual(hearing_result, self.whisper)


if __name__ == "__main__":
    unittest.main()