from features.external_tools.external_tool import ExternalToolProvider

# All providers array is at the end of the file

OPEN_AI = ExternalToolProvider(
    id = "open-ai",
    name = "OpenAI",
    token_management_url = "https://platform.openai.com/api-keys",
    token_format = "sk-...abc123",
    tools = ["ChatGPT", "DALL-E", "Whisper", "Image-1"],
)

ANTHROPIC = ExternalToolProvider(
    id = "anthropic",
    name = "Anthropic",
    token_management_url = "https://console.anthropic.com/settings/keys",
    token_format = "sk-ant-...abc123",
    tools = ["Claude"],
)

PERPLEXITY = ExternalToolProvider(
    id = "perplexity",
    name = "Perplexity",
    token_management_url = "https://www.perplexity.ai/account/api/keys",
    token_format = "pplx-...abc123",
    tools = ["Search", "Research"],
)

REPLICATE = ExternalToolProvider(
    id = "replicate",
    name = "Replicate",
    token_management_url = "https://replicate.com/account/api-tokens",
    token_format = "r8_...abc123",
    tools = ["Photo-Gen, Image-Gen, Image-Edit"],
)

RAPID_API = ExternalToolProvider(
    id = "rapid-api",
    name = "RapidAPI",
    token_management_url = "https://docs.rapidapi.com/docs/configuring-api-security",
    token_format = "abc...123",
    tools = ["Stocks", "X (Twitter)", "Weather"],
)

COINMARKETCAP = ExternalToolProvider(
    id = "coinmarketcap-api",
    name = "CoinMarketCap API",
    token_management_url = "https://pro.coinmarketcap.com/account",
    token_format = "abcd...-...-...1234",
    tools = ["Crypto/Fiat", "Crypto List"],
)

ALL_PROVIDERS = [OPEN_AI, ANTHROPIC, PERPLEXITY, REPLICATE, RAPID_API, COINMARKETCAP]
