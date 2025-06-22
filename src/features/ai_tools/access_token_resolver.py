from uuid import UUID

from pydantic import SecretStr

from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.schema.sponsorship import Sponsorship
from db.schema.user import User
from features.ai_tools.external_ai_tool import ExternalAiTool, ToolProvider
from features.ai_tools.external_ai_tool_provider_library import (
    ANTHROPIC,
    COINMARKETCAP,
    OPEN_AI,
    PERPLEXITY,
    RAPID_API,
    REPLICATE,
)
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin


class TokenResolutionError(Exception):

    def __init__(self, tool_provider: ToolProvider, tool: ExternalAiTool | None = None):
        message = f"Unable to resolve an access token for '{tool_provider.name}'"
        if tool:
            message += f" - '{tool.name}'"
        super().__init__(message)


class AccessTokenResolver(SafePrinterMixin):
    __invoker: User
    __user_dao: UserCRUD
    __sponsorship_dao: SponsorshipCRUD

    def __init__(
        self,
        user_dao: UserCRUD,
        sponsorship_dao: SponsorshipCRUD,
        invoker_user: User | None = None,
        invoker_user_id_hex: str | None = None,
    ):
        super().__init__(config.verbose)
        self.__user_dao = user_dao
        self.__sponsorship_dao = sponsorship_dao
        self.__validate(invoker_user, invoker_user_id_hex)

    def __validate(self, invoker_user: User | None, invoker_user_id_hex: str | None):
        # nothing is provided
        if invoker_user is None and invoker_user_id_hex is None:
            message = "Either invoker_user or invoker_user_id_hex must be provided"
            self.sprint(message)
            raise ValueError(message)
        # invoker object is provided
        if invoker_user is not None:
            self.sprint(f"AccessTokenResolver initialized with user object '{invoker_user.id.hex}'")
            self.__invoker = invoker_user
            return
        # only the ID is provided
        invoker_user_db = self.__user_dao.get(UUID(hex = invoker_user_id_hex))
        if not invoker_user_db:
            message = f"Invoker user '{invoker_user_id_hex}' not found"
            self.sprint(message)
            raise ValueError(message)
        self.__invoker = User.model_validate(invoker_user_db)

    def require_access_token_for_tool(self, tool: ExternalAiTool) -> SecretStr:
        token = self.get_access_token_for_tool(tool)
        if token is None:
            raise TokenResolutionError(tool.provider, tool)
        return token

    def require_access_token(self, provider: ToolProvider) -> SecretStr:
        token = self.get_access_token(provider)
        if token is None:
            raise TokenResolutionError(provider)
        return token

    def get_access_token_for_tool(self, tool: ExternalAiTool) -> SecretStr | None:
        self.sprint(f"Resolving access token for tool '{tool.id}'")
        return self.get_access_token(tool.provider)

    def get_access_token(self, provider: ToolProvider) -> SecretStr | None:
        self.sprint(f"Resolving access token for provider '{provider.id}'")

        # check if invoker has direct token
        user_token = self.__get_user_token_for_provider(self.__invoker, provider)
        if user_token:
            self.sprint(f"Found direct token for provider '{provider.id}'")
            return SecretStr(user_token)
        self.sprint("No direct token found for invoker user")

        # check if invoker has a sponsorship
        sponsorships_db = self.__sponsorship_dao.get_all_by_receiver(self.__invoker.id, limit = 1)
        if not sponsorships_db:
            self.sprint(f"User '{self.__invoker.id.hex}' has no sponsorships")
            return None

        # get sponsor and check their token
        self.sprint("Checking sponsorships for invoker user now")
        sponsorship = Sponsorship.model_validate(sponsorships_db[0])
        sponsor_user_db = self.__user_dao.get(sponsorship.sponsor_id)
        if not sponsor_user_db:
            self.sprint(f"Sponsor '{sponsorship.sponsor_id.hex}' not found")
            return None
        sponsor_user = User.model_validate(sponsor_user_db)

        # check sponsor's token for this provider
        sponsor_token = self.__get_user_token_for_provider(sponsor_user, provider)
        if sponsor_token:
            self.sprint(f"Found sponsor token for provider '{provider.id}'")
            return SecretStr(sponsor_token)

        self.sprint(f"No token found for provider '{provider.id}'")
        return None

    def __get_user_token_for_provider(self, user: User, provider: ToolProvider) -> str | None:
        match provider.id:
            case OPEN_AI.id:
                return user.open_ai_key
            case ANTHROPIC.id:
                return user.anthropic_key
            case PERPLEXITY.id:
                return user.perplexity_key
            case REPLICATE.id:
                return user.replicate_key
            case RAPID_API.id:
                return user.rapid_api_key
            case COINMARKETCAP.id:
                return user.coinmarketcap_key
        self.sprint(f"Unknown provider '{provider.id}'")
        return None
