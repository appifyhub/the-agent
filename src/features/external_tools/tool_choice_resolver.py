from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.schema.sponsorship import Sponsorship
from db.schema.user import User
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import ALL_EXTERNAL_TOOLS
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


class ToolChoiceResolutionError(Exception):

    def __init__(self, tool_type: ToolType, preferred_tool: ExternalTool | None = None):
        message = f"Unable to resolve a tool choice for type '{tool_type.value}'"
        if preferred_tool:
            message += f" - preferred tool '{preferred_tool.name}' is not available"
        message += ". Check your profile settings page."
        super().__init__(message)


class ToolChoiceResolver(SafePrinterMixin):
    __invoker: User
    __user_dao: UserCRUD
    __sponsorship_dao: SponsorshipCRUD

    def __init__(
        self,
        invoker_user: User,
        user_dao: UserCRUD,
        sponsorship_dao: SponsorshipCRUD,
    ):
        super().__init__(config.verbose)
        self.__invoker = invoker_user
        self.__user_dao = user_dao
        self.__sponsorship_dao = sponsorship_dao

    def require_choice(self, tool_type: ToolType, preferred: ExternalTool | None = None) -> ExternalTool:
        """
        Get a required tool choice for the given type. Raises exception if no choice is available.
        
        Args:
            tool_type: The type of tool needed
            preferred: Optional preferred tool to try first
            
        Returns:
            The selected ExternalTool
            
        Raises:
            ToolChoiceResolutionError: If no suitable tool can be found
        """
        tool = self.get_choice(tool_type, preferred)
        if tool is None:
            raise ToolChoiceResolutionError(tool_type, preferred)
        return tool

    def get_choice(self, tool_type: ToolType, preferred: ExternalTool | None = None) -> ExternalTool | None:
        """
        Get a tool choice for the given type, with optional fallback tool.
        
        Args:
            tool_type: The type of tool needed
            preferred: Optional fallback tool to use if user's choice is not available
            
        Returns:
            The selected ExternalTool or None if no suitable tool is found
            
        Note:
            This method only resolves tool preferences, not access tokens. The caller
            should use AccessTokenResolver to verify the user can actually use the returned tool.
        """
        self.sprint(f"Resolving tool choice for type '{tool_type.value}'")
        
        # Check invoker's direct tool choice first
        user_choice_id = self.__get_user_tool_choice_for_type(self.__invoker, tool_type)
        if user_choice_id:
            tool = self.__find_tool_by_id(user_choice_id)
            if tool and tool_type in tool.types:
                self.sprint(f"Found direct user choice '{user_choice_id}' for type '{tool_type.value}'")
                return tool
            else:
                self.sprint(f"User choice '{user_choice_id}' not found or invalid for type '{tool_type.value}'")

        # Check if invoker has a sponsorship
        sponsorships_db = self.__sponsorship_dao.get_all_by_receiver(self.__invoker.id, limit = 1)
        if sponsorships_db:
            # Get sponsor and check their tool choice
            self.sprint("Checking sponsorships for tool choices")
            sponsorship = Sponsorship.model_validate(sponsorships_db[0])
            sponsor_user_db = self.__user_dao.get(sponsorship.sponsor_id)
            if sponsor_user_db:
                sponsor_user = User.model_validate(sponsor_user_db)
                sponsor_choice_id = self.__get_user_tool_choice_for_type(sponsor_user, tool_type)
                if sponsor_choice_id:
                    tool = self.__find_tool_by_id(sponsor_choice_id)
                    if tool and tool_type in tool.types:
                        self.sprint(f"Found sponsor choice '{sponsor_choice_id}' for type '{tool_type.value}'")
                        return tool
            else:
                self.sprint(f"Sponsor '{sponsorship.sponsor_id.hex}' not found")
        else:
            self.sprint(f"User '{self.__invoker.id.hex}' has no sponsorships")

        # Try fallback/preferred tool if specified and valid
        if preferred and tool_type in preferred.types:
            self.sprint(f"Using fallback tool '{preferred.id}' for type '{tool_type.value}'")
            return preferred
        elif preferred:
            self.sprint(f"Fallback tool '{preferred.id}' does not support type '{tool_type.value}'")

        # Finally, use system default
        self.sprint(f"No tool choice found for type '{tool_type.value}', using system default")
        return self.__get_default_tool_for_type(tool_type)

    def __get_user_tool_choice_for_type(self, user: User, tool_type: ToolType) -> str | None:
        """Get the user's configured tool choice for the given type."""
        match tool_type:
            case ToolType.llm:
                return user.tool_choice_llm
            case ToolType.vision:
                return user.tool_choice_vision
            case ToolType.hearing:
                return user.tool_choice_hearing
            case ToolType.images:
                return user.tool_choice_images
            case ToolType.search:
                return user.tool_choice_search
            case ToolType.embedding:
                return user.tool_choice_embedding
            case ToolType.api:
                return user.tool_choice_api
        self.sprint(f"Unknown tool type '{tool_type.value}'")
        return None

    def __find_tool_by_id(self, tool_id: str) -> ExternalTool | None:
        """Find an external tool by its ID."""
        for tool in ALL_EXTERNAL_TOOLS:
            if tool.id == tool_id:
                return tool
        return None

    def __get_default_tool_for_type(self, tool_type: ToolType) -> ExternalTool | None:
        """Get the first available tool for the given type as a default."""
        for tool in ALL_EXTERNAL_TOOLS:
            if tool_type in tool.types:
                self.sprint(f"Using default tool '{tool.id}' for type '{tool_type.value}'")
                return tool
        self.sprint(f"No default tool found for type '{tool_type.value}'")
        return None