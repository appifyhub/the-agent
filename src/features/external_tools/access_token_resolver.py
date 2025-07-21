from pydantic import SecretStr

from db.schema.sponsorship import Sponsorship
from db.schema.user import User
from di.di import DI
from features.external_tools.external_tool import ExternalTool, ExternalToolProvider
from features.external_tools.external_tool_provider_library import (
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

    def __init__(self, tool_provider: ExternalToolProvider, tool: ExternalTool | None = None):
        message = f"Unable to resolve an access token for '{tool_provider.name}'"
        if tool:
            message += f" - '{tool.name}'"
        message += ". Check your profile settings page."
        super().__init__(message)


class AccessTokenResolver(SafePrinterMixin):
    __di: DI

    def __init__(self, di: DI):
        super().__init__(config.verbose)
        self.__di = di

    def require_access_token_for_tool(self, tool: ExternalTool) -> SecretStr:
        token = self.get_access_token_for_tool(tool)
        if token is None:
            raise TokenResolutionError(tool.provider, tool)
        return token

    def require_access_token(self, provider: ExternalToolProvider) -> SecretStr:
        token = self.get_access_token(provider)
        if token is None:
            raise TokenResolutionError(provider)
        return token

    def get_access_token_for_tool(self, tool: ExternalTool) -> SecretStr | None:
        self.sprint(f"Resolving access token for tool '{tool.id}'")
        return self.get_access_token(tool.provider)

    def get_access_token(self, provider: ExternalToolProvider) -> SecretStr | None:
        self.sprint(f"Resolving access token for provider '{provider.id}'")

        # check if invoker has a direct token
        user_token = self.__get_user_token_for_provider(self.__di.invoker, provider)
        if user_token:
            self.sprint(f"Found direct token for provider '{provider.id}'")
            return SecretStr(user_token)
        self.sprint("No direct token found for invoker user")

        # check if invoker has a sponsorship
        sponsorships_db = self.__di.sponsorship_crud.get_all_by_receiver(self.__di.invoker.id, limit = 1)
        if not sponsorships_db:
            self.sprint(f"User '{self.__di.invoker.id.hex}' has no sponsorships")
            return None

        # get sponsor and check their token
        self.sprint("Checking sponsorships for invoker user now")
        sponsorship = Sponsorship.model_validate(sponsorships_db[0])
        sponsor_user_db = self.__di.user_crud.get(sponsorship.sponsor_id)
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

    def __get_user_token_for_provider(self, user: User, provider: ExternalToolProvider) -> str | None:
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
