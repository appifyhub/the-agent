from features.external_tools.external_tool import CostEstimate, ExternalTool, ToolType
from features.external_tools.external_tool_provider_library import (
    ANTHROPIC,
    COINMARKETCAP,
    GOOGLE_AI,
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
    cost_estimate = CostEstimate(
        input_1m_tokens = 50,
        output_1m_tokens = 150,
    ),
)

GPT_4 = ExternalTool(
    id = "gpt-4",
    name = "GPT 4",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.copywriting],
    cost_estimate = CostEstimate(
        input_1m_tokens = 200,
        output_1m_tokens = 800,
    ),
)

GPT_4_TURBO = ExternalTool(
    id = "gpt-4-turbo",
    name = "GPT 4 Turbo",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 1000,
        output_1m_tokens = 3000,
    ),
)

GPT_4_1 = ExternalTool(
    id = "gpt-4.1",
    name = "GPT 4.1",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 200,
        output_1m_tokens = 800,
    ),
)

GPT_4_1_MINI = ExternalTool(
    id = "gpt-4.1-mini",
    name = "GPT 4.1 Mini",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 40,
        output_1m_tokens = 160,
    ),
)

GPT_4_1_NANO = ExternalTool(
    id = "gpt-4.1-nano",
    name = "GPT 4.1 Nano",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 10,
        output_1m_tokens = 40,
    ),
)

GPT_5 = ExternalTool(
    id = "gpt-5",
    name = "GPT 5",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 125,
        output_1m_tokens = 1000,
    ),
)

GPT_5_MINI = ExternalTool(
    id = "gpt-5-mini",
    name = "GPT 5 Mini",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 25,
        output_1m_tokens = 200,
    ),
)

GPT_5_NANO = ExternalTool(
    id = "gpt-5-nano",
    name = "GPT 5 Nano",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 5,
        output_1m_tokens = 40,
    ),
)

GPT_5_1 = ExternalTool(
    id = "gpt-5.1",
    name = "GPT 5.1",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 125,
        output_1m_tokens = 1000,
    ),
)

GPT_5_2 = ExternalTool(
    id = "gpt-5.2",
    name = "GPT 5.2",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 175,
        output_1m_tokens = 1400,
    ),
)

GPT_4O = ExternalTool(
    id = "gpt-4o",
    name = "GPT 4o",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 250,
        output_1m_tokens = 1000,
    ),
)

GPT_4O_MINI = ExternalTool(
    id = "gpt-4o-mini",
    name = "GPT 4o Mini",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 15,
        output_1m_tokens = 60,
    ),
)

GPT_O3_MINI = ExternalTool(
    id = "o3-mini",
    name = "GPT O3 Mini",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting],
    cost_estimate = CostEstimate(
        input_1m_tokens = 110,
        output_1m_tokens = 440,
    ),
)

GPT_O4_MINI = ExternalTool(
    id = "o4-mini",
    name = "GPT O4 Mini",
    provider = OPEN_AI,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 110,
        output_1m_tokens = 440,
    ),
)

GPT_40_TRANSCRIBE = ExternalTool(
    id = "gpt-4o-transcribe",
    name = "GPT 4o Transcribe",
    provider = OPEN_AI,
    types = [ToolType.hearing],
    cost_estimate = CostEstimate(
        input_1m_tokens = 600,
        output_1m_tokens = 1000,
    ),
)

GPT_40_MINI_TRANSCRIBE = ExternalTool(
    id = "gpt-4o-mini-transcribe",
    name = "GPT 4o Mini Transcribe",
    provider = OPEN_AI,
    types = [ToolType.hearing],
    cost_estimate = CostEstimate(
        input_1m_tokens = 300,
        output_1m_tokens = 500,
    ),
)

WHISPER_1 = ExternalTool(
    id = "whisper-1",
    name = "Whisper 1",
    provider = OPEN_AI,
    types = [ToolType.hearing],
    cost_estimate = CostEstimate(
        second_of_runtime = 0.01,
    ),
)

TEXT_EMBEDDING_3_SMALL = ExternalTool(
    id = "text-embedding-3-small",
    name = "Text Embedding 3 Small",
    provider = OPEN_AI,
    types = [ToolType.embedding],
    cost_estimate = CostEstimate(
        input_1m_tokens = 2,
        output_1m_tokens = 2,  # probably useless for embeddings
    ),
)

TEXT_EMBEDDING_5_LARGE = ExternalTool(
    id = "text-embedding-3-large",
    name = "Text Embedding 3 Large",
    provider = OPEN_AI,
    types = [ToolType.embedding],
    cost_estimate = CostEstimate(
        input_1m_tokens = 15,
        output_1m_tokens = 15,  # probably useless for embeddings
    ),
)

###  Anthropic  ###

CLAUDE_3_5_HAIKU = ExternalTool(
    id = "claude-3-5-haiku-latest",
    name = "Claude 3.5 Haiku",
    provider = ANTHROPIC,
    types = [ToolType.chat, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 80,
        output_1m_tokens = 400,
        search_1m_tokens = 40,  # used with vision queries
    ),
)

CLAUDE_3_7_SONNET = ExternalTool(
    id = "claude-3-7-sonnet-latest",
    name = "Claude 3.7 Sonnet",
    provider = ANTHROPIC,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 300,
        output_1m_tokens = 1500,
        search_1m_tokens = 150,  # used with vision queries
    ),
)

CLAUDE_4_SONNET = ExternalTool(
    id = "claude-sonnet-4-0",
    name = "Claude 4 Sonnet",
    provider = ANTHROPIC,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 300,
        output_1m_tokens = 1500,
        search_1m_tokens = 150,  # used with vision queries
    ),
)

CLAUDE_4_5_HAIKU = ExternalTool(
    id = "claude-haiku-4-5",
    name = "Claude Haiku 4.5",
    provider = ANTHROPIC,
    types = [ToolType.chat, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 100,
        output_1m_tokens = 500,
        search_1m_tokens = 50,  # used with vision queries
    ),
)

CLAUDE_4_5_SONNET = ExternalTool(
    id = "claude-sonnet-4-5",
    name = "Claude 4.5 Sonnet",
    provider = ANTHROPIC,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 300,
        output_1m_tokens = 1500,
        search_1m_tokens = 150,  # used with vision queries
    ),
)

###  Google AI  ###

GEMINI_2_5_FLASH_LITE = ExternalTool(
    id = "gemini-2.5-flash-lite",
    name = "Gemini 2.5 Flash-Lite",
    provider = GOOGLE_AI,
    types = [ToolType.chat, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 10,
        output_1m_tokens = 40,
        search_1m_tokens = 5,  # used with vision queries
    ),
)

GEMINI_2_5_FLASH = ExternalTool(
    id = "gemini-2.5-flash",
    name = "Gemini 2.5 Flash",
    provider = GOOGLE_AI,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 30,
        output_1m_tokens = 250,
        search_1m_tokens = 15,  # used with vision queries
    ),
)

GEMINI_2_5_PRO = ExternalTool(
    id = "gemini-2.5-pro",
    name = "Gemini 2.5 Pro",
    provider = GOOGLE_AI,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 190,
        output_1m_tokens = 1250,
        search_1m_tokens = 95,  # used with vision queries
    ),
)

GEMINI_3_FLASH = ExternalTool(
    id = "gemini-3-flash-preview",
    name = "Gemini 3 Flash (Preview)",
    provider = GOOGLE_AI,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 50,
        output_1m_tokens = 300,
        search_1m_tokens = 25,  # used with vision queries
    ),
)

GEMINI_3_PRO = ExternalTool(
    id = "gemini-3-pro-preview",
    name = "Gemini 3 Pro (Preview)",
    provider = GOOGLE_AI,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting, ToolType.vision],
    cost_estimate = CostEstimate(
        input_1m_tokens = 300,
        output_1m_tokens = 1500,
        search_1m_tokens = 150,  # used with vision queries
    ),
)

GEMINI_3_PRO_IMAGE = ExternalTool(
    id = "gemini-3-pro-image-preview",
    name = "Gemini 3 Pro Image",
    provider = GOOGLE_AI,
    types = [ToolType.images_gen],
    cost_estimate = CostEstimate(
        input_1m_tokens = 200,
        output_1m_tokens = 12000,
        image_1k = 14,
        image_2k = 14,
        image_4k = 24,
    ),
)

###  Perplexity  ###

SONAR = ExternalTool(
    id = "sonar",
    name = "Sonar",
    provider = PERPLEXITY,
    types = [ToolType.chat, ToolType.copywriting, ToolType.search],
    cost_estimate = CostEstimate(
        input_1m_tokens = 100,
        output_1m_tokens = 100,
        search_1m_tokens = 300,
        api_call = 1,
    ),
)

SONAR_PRO = ExternalTool(
    id = "sonar-pro",
    name = "Sonar Pro",
    provider = PERPLEXITY,
    types = [ToolType.chat, ToolType.copywriting, ToolType.search],
    cost_estimate = CostEstimate(
        input_1m_tokens = 300,
        output_1m_tokens = 1500,
        search_1m_tokens = 300,
        api_call = 1,
    ),
)

SONAR_REASONING_PRO = ExternalTool(
    id = "sonar-reasoning-pro",
    name = "Sonar Reasoning Pro",
    provider = PERPLEXITY,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting, ToolType.search],
    cost_estimate = CostEstimate(
        input_1m_tokens = 200,
        output_1m_tokens = 800,
        search_1m_tokens = 300,
        api_call = 1,
    ),
)

SONAR_DEEP_RESEARCH = ExternalTool(
    id = "sonar-deep-research",
    name = "Sonar Deep Research",
    provider = PERPLEXITY,
    types = [ToolType.chat, ToolType.reasoning, ToolType.copywriting, ToolType.search],
    cost_estimate = CostEstimate(
        input_1m_tokens = 200,
        output_1m_tokens = 800,
        search_1m_tokens = 300,
        api_call = 5,
    ),
)

###  Rapid API  ###

FIAT_CURRENCY_EXCHANGE = ExternalTool(
    id = "currency-converter5.p.rapidapi.com",
    name = "RapidAPI's Fiat Converter",
    provider = RAPID_API,
    types = [ToolType.api_fiat_exchange],
    cost_estimate = CostEstimate(
        api_call = 0,
    ),
)

TWITTER_API = ExternalTool(
    id = "twitter-api-v1-1-enterprise.p.rapidapi.com",
    name = "RapidAPI's Twitter API",
    provider = RAPID_API,
    types = [ToolType.api_twitter],
    cost_estimate = CostEstimate(
        api_call = 0,
    ),
)

###  CoinMarketCap API  ###

CRYPTO_CURRENCY_EXCHANGE = ExternalTool(
    id = "v1.cryptocurrency.quotes.latest",
    name = "CoinMarketCap's Crypto Converter",
    provider = COINMARKETCAP,
    types = [ToolType.api_crypto_exchange],
    cost_estimate = CostEstimate(
        api_call = 0,
    ),
)

###  Replicate  ###

IMAGE_GENERATION_FLUX_1_1 = ExternalTool(
    id = "black-forest-labs/flux-1.1-pro",
    name = "Black Forest's Flux 1.1 Pro",
    provider = REPLICATE,
    types = [ToolType.images_gen],
    cost_estimate = CostEstimate(
        image_1k = 4,
        image_2k = 4,
        image_4k = 4,
    ),
)

IMAGE_GENERATION_EDITING_FLUX_2_PRO = ExternalTool(
    id = "black-forest-labs/flux-2-pro",
    name = "Black Forest's Flux 2 Pro",
    provider = REPLICATE,
    types = [ToolType.images_gen, ToolType.images_edit],
    cost_estimate = CostEstimate(
        image_1k = 8,
        image_2k = 10,
        image_4k = 12,
    ),
)

IMAGE_GENERATION_EDITING_FLUX_2_MAX = ExternalTool(
    id = "black-forest-labs/flux-2-max",
    name = "Black Forest's Flux 2 Max",
    provider = REPLICATE,
    types = [ToolType.images_gen, ToolType.images_edit],
    cost_estimate = CostEstimate(
        image_1k = 16,
        image_2k = 20,
        image_4k = 25,
    ),
)

IMAGE_GENERATION_EDITING_GPT_IMAGE_1_5 = ExternalTool(
    id = "openai/gpt-image-1.5",
    name = "OpenAI's GPT Image 1.5",
    provider = REPLICATE,
    types = [ToolType.images_gen, ToolType.images_edit],
    cost_estimate = CostEstimate(
        image_1k = 15,
        image_2k = 15,
        image_4k = 15,
    ),
)

IMAGE_EDITING_FLUX_KONTEXT_PRO = ExternalTool(
    id = "black-forest-labs/flux-kontext-pro",
    name = "Black Forest's Flux Kontext Pro",
    provider = REPLICATE,
    types = [ToolType.images_gen, ToolType.images_edit],
    cost_estimate = CostEstimate(
        image_1k = 4,
        image_2k = 4,
        image_4k = 4,
    ),
)

IMAGE_EDITING_SEED_EDIT_3 = ExternalTool(
    id = "bytedance/seededit-3.0",
    name = "ByteDance's SeedEdit v3",
    provider = REPLICATE,
    types = [ToolType.images_edit],
    cost_estimate = CostEstimate(
        image_1k = 3,
        image_2k = 3,
        image_4k = 3,
    ),
)

IMAGE_GENERATION_EDITING_SEEDREAM_4 = ExternalTool(
    id = "bytedance/seedream-4",
    name = "ByteDance's SeeDream v4",
    provider = REPLICATE,
    types = [ToolType.images_gen, ToolType.images_edit],
    cost_estimate = CostEstimate(
        image_1k = 4,
        image_2k = 4,
        image_4k = 4,
    ),
)

IMAGE_GENERATION_GEMINI_2_5_FLASH_IMAGE = ExternalTool(
    id = "google/gemini-2.5-flash-image",
    name = "Google's Gemini 2.5 Flash Image",
    provider = REPLICATE,
    types = [ToolType.images_gen],
    cost_estimate = CostEstimate(
        input_1m_tokens = 30,
        image_1k = 4,
        image_2k = 4,
        image_4k = 4,
    ),
)

IMAGE_EDITING_GOOGLE_NANO_BANANA = ExternalTool(
    id = "google/nano-banana",
    name = "Google's Nano Banana",
    provider = REPLICATE,
    types = [ToolType.images_gen, ToolType.images_edit],
    cost_estimate = CostEstimate(
        image_1k = 4,
        image_2k = 4,
        image_4k = 4,
    ),
)

IMAGE_EDITING_GOOGLE_NANO_BANANA_PRO = ExternalTool(
    id = "google/nano-banana-pro",
    name = "Google's Nano Banana Pro",
    provider = REPLICATE,
    types = [ToolType.images_gen, ToolType.images_edit],
    cost_estimate = CostEstimate(
        image_1k = 15,
        image_2k = 15,
        image_4k = 30,
    ),
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
    GPT_5,
    GPT_5_MINI,
    GPT_5_NANO,
    GPT_5_1,
    GPT_5_2,
    GPT_4O,
    GPT_4O_MINI,
    GPT_O3_MINI,
    GPT_O4_MINI,
    GPT_40_TRANSCRIBE,
    GPT_40_MINI_TRANSCRIBE,
    WHISPER_1,
    TEXT_EMBEDDING_3_SMALL,
    TEXT_EMBEDDING_5_LARGE,
    # Anthropic
    CLAUDE_3_5_HAIKU,
    CLAUDE_3_7_SONNET,
    CLAUDE_4_SONNET,
    CLAUDE_4_5_HAIKU,
    CLAUDE_4_5_SONNET,
    # Google AI
    GEMINI_2_5_FLASH_LITE,
    GEMINI_2_5_FLASH,
    GEMINI_2_5_PRO,
    GEMINI_3_FLASH,
    GEMINI_3_PRO,
    GEMINI_3_PRO_IMAGE,
    # Perplexity
    SONAR,
    SONAR_PRO,
    SONAR_REASONING_PRO,
    SONAR_DEEP_RESEARCH,
    # Rapid API
    FIAT_CURRENCY_EXCHANGE,
    TWITTER_API,
    # CoinMarketCap
    CRYPTO_CURRENCY_EXCHANGE,
    # Replicate
    IMAGE_GENERATION_FLUX_1_1,
    IMAGE_GENERATION_EDITING_FLUX_2_PRO,
    IMAGE_GENERATION_EDITING_FLUX_2_MAX,
    IMAGE_GENERATION_EDITING_GPT_IMAGE_1_5,
    IMAGE_EDITING_FLUX_KONTEXT_PRO,
    IMAGE_EDITING_SEED_EDIT_3,
    IMAGE_GENERATION_EDITING_SEEDREAM_4,
    IMAGE_GENERATION_GEMINI_2_5_FLASH_IMAGE,
    IMAGE_EDITING_GOOGLE_NANO_BANANA,
    IMAGE_EDITING_GOOGLE_NANO_BANANA_PRO,
]
