from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_provider_library import (
    ANTHROPIC,
    COINMARKETCAP,
    OPEN_AI,
    PERPLEXITY,
    RAPID_API,
    REPLICATE,
)

# Tools arrays are at the end of the file

###  Open AI  ###

GPT_3_5_TURBO = ExternalTool(
    id = "gpt-3.5-turbo",
    name = "GPT 3.5 Turbo",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.copywriting],
)

GPT_4 = ExternalTool(
    id = "gpt-4",
    name = "GPT 4",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.copywriting],
)

GPT_4_TURBO = ExternalTool(
    id = "gpt-4-turbo",
    name = "GPT 4 Turbo",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.copywriting, ToolType.vision],
)

GPT_4_1 = ExternalTool(
    id = "gpt-4.1",
    name = "GPT 4.1",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.copywriting, ToolType.vision],
)

GPT_4_1_MINI = ExternalTool(
    id = "gpt-4.1-mini",
    name = "GPT 4.1 Mini",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.copywriting, ToolType.vision],
)

GPT_4_1_NANO = ExternalTool(
    id = "gpt-4.1-nano",
    name = "GPT 4.1 Nano",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.copywriting, ToolType.vision],
)

GPT_4O = ExternalTool(
    id = "gpt-4o",
    name = "GPT 4o",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.copywriting, ToolType.vision],
)

GPT_4O_MINI = ExternalTool(
    id = "gpt-4o-mini",
    name = "GPT 4o Mini",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.copywriting, ToolType.vision],
)

GPT_O3_MINI = ExternalTool(
    id = "o3-mini",
    name = "GPT O3 Mini",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting],
)

GPT_O4_MINI = ExternalTool(
    id = "o4-mini",
    name = "GPT O4 Mini",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting, ToolType.vision],
)

GPT_40_TRANSCRIBE = ExternalTool(
    id = "gpt-4o-transcribe",
    name = "GPT 4o Transcribe",
    provider = OPEN_AI,
    types = [ToolType.hearing],
)

GPT_40_MINI_TRANSCRIBE = ExternalTool(
    id = "gpt-4o-mini-transcribe",
    name = "GPT 4o Mini Transcribe",
    provider = OPEN_AI,
    types = [ToolType.hearing],
)

WHISPER_1 = ExternalTool(
    id = "whisper-1",
    name = "Whisper 1",
    provider = OPEN_AI,
    types = [ToolType.hearing],
)

GPT_IMAGE_1 = ExternalTool(
    id = "gpt-image-1",
    name = "GPT Image 1",
    provider = OPEN_AI,
    types = [ToolType.images_gen, ToolType.images_edit],
)

TEXT_EMBEDDING_3_SMALL = ExternalTool(
    id = "text-embedding-3-small",
    name = "Text Embedding 3 Small",
    provider = OPEN_AI,
    types = [ToolType.embedding],
)

TEXT_EMBEDDING_5_LARGE = ExternalTool(
    id = "text-embedding-3-large",
    name = "Text Embedding 3 Large",
    provider = OPEN_AI,
    types = [ToolType.embedding],
)

###  Anthropic  ###

CLAUDE_3_5_HAIKU = ExternalTool(
    id = "claude-3-5-haiku-latest",
    name = "Claude 3.5 Haiku",
    provider = ANTHROPIC,
    types = [ToolType.chat, ToolType.copywriting, ToolType.vision],
)

CLAUDE_3_5_SONNET = ExternalTool(
    id = "claude-3-5-sonnet-latest",
    name = "Claude 3.5 Sonnet",
    provider = ANTHROPIC,
    types = [ToolType.chat, ToolType.copywriting, ToolType.vision],
)

CLAUDE_3_7_SONNET = ExternalTool(
    id = "claude-3-7-sonnet-latest",
    name = "Claude 3.7 Sonnet",
    provider = ANTHROPIC,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting, ToolType.vision],
)

CLAUDE_4_SONNET = ExternalTool(
    id = "claude-sonnet-4-0",
    name = "Claude 4 Sonnet",
    provider = ANTHROPIC,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting, ToolType.vision],
)

###  Perplexity  ###

SONAR = ExternalTool(
    id = "sonar",
    name = "Sonar",
    provider = PERPLEXITY,
    types = [ToolType.chat, ToolType.copywriting, ToolType.search],
)

SONAR_PRO = ExternalTool(
    id = "sonar-pro",
    name = "Sonar Pro",
    provider = PERPLEXITY,
    types = [ToolType.chat, ToolType.copywriting, ToolType.search],
)

SONAR_REASONING = ExternalTool(
    id = "sonar-reasoning",
    name = "Sonar Reasoning",
    provider = PERPLEXITY,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting, ToolType.search],
)

SONAR_REASONING_PRO = ExternalTool(
    id = "sonar-reasoning-pro",
    name = "Sonar Reasoning Pro",
    provider = PERPLEXITY,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting, ToolType.search],
)

SONAR_DEEP_RESEARCH = ExternalTool(
    id = "sonar-deep-research",
    name = "Sonar Deep Research",
    provider = PERPLEXITY,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting, ToolType.search],
)

###  Rapid API  ###

FIAT_CURRENCY_EXCHANGE = ExternalTool(
    id = "currency-converter5.p.rapidapi.com",
    name = "RapidAPI's Fiat Converter",
    provider = RAPID_API,
    types = [ToolType.api_fiat_exchange],
)

TWITTER_API = ExternalTool(
    id = "twitter-api-v1-1-enterprise.p.rapidapi.com",
    name = "RapidAPI's Twitter API",
    provider = RAPID_API,
    types = [ToolType.api_twitter],
)

###  CoinMarketCap API  ###

CRYPTO_CURRENCY_EXCHANGE = ExternalTool(
    id = "v1.cryptocurrency.quotes.latest",
    name = "CoinMarketCap's Crypto Converter",
    provider = COINMARKETCAP,
    types = [ToolType.api_crypto_exchange],
)

###  Replicate  ###

BACKGROUND_REMOVAL = ExternalTool(
    id = "cjwbw/rembg:fb8af171cfa1616ddcf1242c093f9c46bcada5ad4cf6f2fbe8b81b330ec5c003",
    name = "Chenxi's Background Removal",
    provider = REPLICATE,
    types = [ToolType.images_background_removal],
)

IMAGE_RESTORATION = ExternalTool(
    id = "sczhou/codeformer:cc4956dd26fa5a7185d5660cc9100fab1b8070a1d1654a8bb5eb6d443b020bb2",
    name = "Shangchen's Image Restoration",
    provider = REPLICATE,
    types = [ToolType.images_restoration],
)

IMAGE_INPAINTING = ExternalTool(
    id = "fermatresearch/magic-image-refiner:507ddf6f977a7e30e46c0daefd30de7d563c72322f9e4cf7cbac52ef0f667b13",
    name = "Fermat Research's Image Inpainting",
    provider = REPLICATE,
    types = [ToolType.images_inpainting],
)

IMAGE_GENERATION_FLUX = ExternalTool(
    id = "black-forest-labs/flux-1.1-pro",
    name = "Black Forest's Flux Pro 1.1",
    provider = REPLICATE,
    types = [ToolType.images_gen],
)

IMAGE_EDITING_FLUX_KONTEXT_PRO = ExternalTool(
    id = "black-forest-labs/flux-kontext-pro",
    name = "Black Forest's Flux Kontext Pro",
    provider = REPLICATE,
    types = [ToolType.images_edit],
)

###  All External Tools  ###

ALL_EXTERNAL_TOOLS = [
    # Open AI
    GPT_3_5_TURBO,
    GPT_4,
    GPT_4_TURBO,
    GPT_4_1,
    GPT_4_1_MINI,
    GPT_4_1_NANO,
    GPT_4O,
    GPT_4O_MINI,
    GPT_O3_MINI,
    GPT_O4_MINI,
    GPT_40_TRANSCRIBE,
    GPT_40_MINI_TRANSCRIBE,
    WHISPER_1,
    GPT_IMAGE_1,
    TEXT_EMBEDDING_3_SMALL,
    TEXT_EMBEDDING_5_LARGE,
    # Anthropic
    CLAUDE_3_5_HAIKU,
    CLAUDE_3_5_SONNET,
    CLAUDE_3_7_SONNET,
    CLAUDE_4_SONNET,
    # Perplexity
    SONAR,
    SONAR_PRO,
    SONAR_REASONING,
    SONAR_REASONING_PRO,
    SONAR_DEEP_RESEARCH,
    # Rapid API
    FIAT_CURRENCY_EXCHANGE,
    TWITTER_API,
    # CoinMarketCap
    CRYPTO_CURRENCY_EXCHANGE,
    # Replicate
    BACKGROUND_REMOVAL,
    IMAGE_RESTORATION,
    IMAGE_INPAINTING,
    IMAGE_GENERATION_FLUX,
]
