from uuid import UUID

from pydantic import SecretStr

from db.schema.sponsorship import Sponsorship
from db.schema.user import User
from di.di import DI
from features.external_tools.external_tool import ExternalTool, ExternalToolProvider
from features.external_tools.external_tool_provider_library import (
    ANTHROPIC,
    COINMARKETCAP,
    GOOGLE_AI,
    OPEN_AI,
    PERPLEXITY,
    RAPID_API,
    REPLICATE,
)
from util import log


class TokenResolutionError(Exception):

    def __init__(self, tool_provider: ExternalToolProvider, tool: ExternalTool | None = None):
        message = f"Unable to resolve an access token for '{tool_provider.name}'"
        if tool:
            message += f" - '{tool.name}'"
        message += ". Check your profile settings page."
        super().__init__(message)


class AccessTokenResolver:

    __di: DI
    __sponsor_cache: dict[str, User | None]

    def __init__(self, di: DI):
        self.__di = di
        self.__sponsor_cache = {}

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
        log.t(f"Resolving access token for tool '{tool.id}'")
        return self.get_access_token(tool.provider)

    def get_access_token(self, provider: ExternalToolProvider) -> SecretStr | None:
        log.t(f"Resolving access token for provider '{provider.id}'")

        # check if invoker has a direct token
        user_token = self.__get_user_token_for_provider(self.__di.invoker, provider)
        if user_token:
            log.t(f"Found direct token for provider '{provider.id}'")
            return user_token
        log.t("No direct token found for invoker user")

        # check if invoker has a sponsorship (with caching)
        sponsor_user = self.__get_sponsor_user(self.__di.invoker.id.hex)
        if not sponsor_user:
            log.t(f"User '{self.__di.invoker.id.hex}' has no sponsor")
            return None

        # check sponsor's token for this provider
        sponsor_token = self.__get_user_token_for_provider(sponsor_user, provider)
        if sponsor_token:
            log.t(f"Found sponsor token for provider '{provider.id}'")
            return sponsor_token

        log.t(f"No token found for provider '{provider.id}'")
        return None

    def __get_sponsor_user(self, user_id_hex: str) -> User | None:
        # check cache first
        if user_id_hex in self.__sponsor_cache:
            log.t(f"Using cached sponsor info for user '{user_id_hex}'")
            return self.__sponsor_cache[user_id_hex]

        # cache miss - fetch from database
        log.t(f"Fetching sponsor info for user '{user_id_hex}' from database")
        user_id = UUID(hex = user_id_hex)
        sponsorships_db = self.__di.sponsorship_crud.get_all_by_receiver(user_id, limit = 1)

        if not sponsorships_db:
            log.t(f"User '{user_id_hex}' has no sponsorships")
            self.__sponsor_cache[user_id_hex] = None
            return None

        # get sponsor user
        log.t("Checking sponsorships for user now")
        sponsorship = Sponsorship.model_validate(sponsorships_db[0])
        sponsor_user_db = self.__di.user_crud.get(sponsorship.sponsor_id)

        if not sponsor_user_db:
            log.t(f"Sponsor '{sponsorship.sponsor_id.hex}' not found")
            self.__sponsor_cache[user_id_hex] = None
            return None

        sponsor_user = User.model_validate(sponsor_user_db)
        self.__sponsor_cache[user_id_hex] = sponsor_user
        log.t(f"Cached sponsor '{sponsor_user.id.hex}' for user '{user_id_hex}'")
        return sponsor_user

    def __get_user_token_for_provider(self, user: User, provider: ExternalToolProvider) -> SecretStr | None:
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
            case GOOGLE_AI.id:
                return user.google_ai_key
        log.t(f"Unknown provider '{provider.id}'")
        return None
