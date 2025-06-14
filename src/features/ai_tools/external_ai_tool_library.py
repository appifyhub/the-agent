from features.ai_tools.external_ai_tool import ExternalAiTool, ToolType
from features.ai_tools.external_ai_tool_provider_library import (
    ANTHROPIC,
    OPEN_AI,
    PERPLEXITY,
    RAPID_API,
    COINMARKETCAP,
    REPLICATE,
)

# Tools arrays are at the end of the file

###  Open AI  ###

GPT_3_5_TURBO = ExternalAiTool(
    id = "gpt-3.5-turbo",
    name = "GPT 3.5 Turbo",
    provider = OPEN_AI,
    types = [ToolType.llm],
)

GPT_4 = ExternalAiTool(
    id = "gpt-4",
    name = "GPT 4",
    provider = OPEN_AI,
    types = [ToolType.llm],
)

GPT_4_TURBO = ExternalAiTool(
    id = "gpt-4-turbo",
    name = "GPT 4 Turbo",
    provider = OPEN_AI,
    types = [ToolType.llm, ToolType.vision],
)

GPT_4_1 = ExternalAiTool(
    id = "gpt-4.1",
    name = "GPT 4.1",
    provider = OPEN_AI,
    types = [ToolType.llm, ToolType.vision],
)

GPT_4_1_MINI = ExternalAiTool(
    id = "gpt-4.1-mini",
    name = "GPT 4.1 Mini",
    provider = OPEN_AI,
    types = [ToolType.llm, ToolType.vision],
)

GPT_4_1_NANO = ExternalAiTool(
    id = "gpt-4.1-nano",
    name = "GPT 4.1 Nano",
    provider = OPEN_AI,
    types = [ToolType.llm, ToolType.vision],
)

GPT_4O = ExternalAiTool(
    id = "gpt-4o",
    name = "GPT 4o",
    provider = OPEN_AI,
    types = [ToolType.llm, ToolType.vision],
)

GPT_4O_MINI = ExternalAiTool(
    id = "gpt-4o-mini",
    name = "GPT 4o Mini",
    provider = OPEN_AI,
    types = [ToolType.llm, ToolType.vision],
)

GPT_O3_MINI = ExternalAiTool(
    id = "o3-mini",
    name = "GPT O3 Mini",
    provider = OPEN_AI,
    types = [ToolType.llm],
)

GPT_O4_MINI = ExternalAiTool(
    id = "o4-mini",
    name = "GPT O4 Mini",
    provider = OPEN_AI,
    types = [ToolType.llm, ToolType.vision],
)

GPT_40_TRANSCRIBE = ExternalAiTool(
    id = "gpt-4o-transcribe",
    name = "GPT 4o Transcribe",
    provider = OPEN_AI,
    types = [ToolType.hearing],
)

GPT_40_MINI_TRANSCRIBE = ExternalAiTool(
    id = "gpt-4o-mini-transcribe",
    name = "GPT 4o Mini Transcribe",
    provider = OPEN_AI,
    types = [ToolType.hearing],
)

WHISPER_1 = ExternalAiTool(
    id = "whisper-1",
    name = "Whisper 1",
    provider = OPEN_AI,
    types = [ToolType.hearing],
)

GPT_IMAGE_1 = ExternalAiTool(
    id = "gpt-image-1",
    name = "GPT Image 1",
    provider = OPEN_AI,
    types = [ToolType.images],
)

TEXT_EMBEDDING_3_SMALL = ExternalAiTool(
    id = "text-embedding-3-small",
    name = "Text Embedding 3 Small",
    provider = OPEN_AI,
    types = [ToolType.embedding],
)

TEXT_EMBEDDING_5_LARGE = ExternalAiTool(
    id = "text-embedding-3-large",
    name = "Text Embedding 3 Large",
    provider = OPEN_AI,
    types = [ToolType.embedding],
)

###  Anthropic  ###

CLAUDE_3_5_HAIKU = ExternalAiTool(
    id = "claude-3-5-haiku-latest",
    name = "Claude 3.5 Haiku",
    provider = ANTHROPIC,
    types = [ToolType.llm, ToolType.vision],
)

CLAUDE_3_5_SONNET = ExternalAiTool(
    id = "claude-3-5-sonnet-latest",
    name = "Claude 3.5 Sonnet",
    provider = ANTHROPIC,
    types = [ToolType.llm, ToolType.vision],
)

CLAUDE_3_7_SONNET = ExternalAiTool(
    id = "claude-3-7-sonnet-latest",
    name = "Claude 3.7 Sonnet",
    provider = ANTHROPIC,
    types = [ToolType.llm, ToolType.vision],
)

CLAUDE_4_SONNET = ExternalAiTool(
    id = "claude-sonnet-4-0",
    name = "Claude 4 Sonnet",
    provider = ANTHROPIC,
    types = [ToolType.llm, ToolType.vision],
)

###  Perplexity  ###

SONAR = ExternalAiTool(
    id = "sonar",
    name = "Sonar",
    provider = PERPLEXITY,
    types = [ToolType.llm, ToolType.search],
)

SONAR_PRO = ExternalAiTool(
    id = "sonar-pro",
    name = "Sonar Pro",
    provider = PERPLEXITY,
    types = [ToolType.llm, ToolType.search],
)

SONAR_REASONING = ExternalAiTool(
    id = "sonar-reasoning",
    name = "Sonar Reasoning",
    provider = PERPLEXITY,
    types = [ToolType.llm, ToolType.search],
)

SONAR_REASONING_PRO = ExternalAiTool(
    id = "sonar-reasoning-pro",
    name = "Sonar Reasoning Pro",
    provider = PERPLEXITY,
    types = [ToolType.llm, ToolType.search],
)

SONAR_DEEP_RESEARCH = ExternalAiTool(
    id = "sonar-deep-research",
    name = "Sonar Deep Research",
    provider = PERPLEXITY,
    types = [ToolType.llm, ToolType.search],
)

###  Rapid API  ###

FIAT_CURRENCY_EXCHANGE = ExternalAiTool(
    id = "currency-converter5.p.rapidapi.com",
    name = "RapidAPI's Fiat Converter",
    provider = RAPID_API,
    types = [ToolType.api],
)

TWITTER_API = ExternalAiTool(
    id = "twitter-api-v1-1-enterprise.p.rapidapi.com",
    name = "RapidAPI's Twitter API",
    provider = RAPID_API,
    types = [ToolType.api],
)

###  CoinMarketCap API  ###

CRYPTO_CURRENCY_EXCHANGE = ExternalAiTool(
    id = "v1.cryptocurrency.quotes.latest",
    name = "CoinMarketCap's Crypto Converter",
    provider = COINMARKETCAP,
    types = [ToolType.api],
)

###  Replicate  ###

BACKGROUND_REMOVAL = ExternalAiTool(
    id = "cjwbw/rembg:fb8af171cfa1616ddcf1242c093f9c46bcada5ad4cf6f2fbe8b81b330ec5c003",
    name = "Chenxi's Background Removal",
    provider = REPLICATE,
    types = [ToolType.images],
)

IMAGE_RESTORATION = ExternalAiTool(
    id = "sczhou/codeformer:cc4956dd26fa5a7185d5660cc9100fab1b8070a1d1654a8bb5eb6d443b020bb2",
    name = "Shangchen's Image Restoration",
    provider = REPLICATE,
    types = [ToolType.images],
)

IMAGE_INPAINTING = ExternalAiTool(
    id = "fermatresearch/magic-image-refiner:507ddf6f977a7e30e46c0daefd30de7d563c72322f9e4cf7cbac52ef0f667b13",
    name = "Fermat Research's Image Inpainting",
    provider = REPLICATE,
    types = [ToolType.images],
)

IMAGE_GENERATION_FLUX = ExternalAiTool(
    id = "black-forest-labs/flux-1.1-pro",
    name = "Black Forest's Flux Pro 1.1",
    provider = REPLICATE,
    types = [ToolType.images],
)

IMAGE_EDITING_FLUX_KONTEXT_PRO = ExternalAiTool(
    id = "black-forest-labs/flux-kontext-pro",
    name = "Black Forest's Flux Kontext Pro",
    provider = REPLICATE,
    types = [ToolType.images],
)

###  All AI Tools  ###

ALL_AI_TOOLS = [
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
