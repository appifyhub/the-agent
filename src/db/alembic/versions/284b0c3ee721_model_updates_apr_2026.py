"""model_updates_apr_2026

Revision ID: 284b0c3ee721
Revises: d05869c0af54
Create Date: 2026-04-26 00:10:03.814538

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "284b0c3ee721"
down_revision: Union[str, None] = "d05869c0af54"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Snapshot of supported model IDs as of 2026-04-26. Hardcoded on purpose:
# the migration must remain stable even if future code changes the model list.
SUPPORTED_MODEL_IDS: tuple[str, ...] = (
    # OpenAI
    "gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini", "gpt-4o-transcribe", "gpt-4o-mini-transcribe",
    "gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-5.1", "gpt-5.2", "gpt-5.4", "gpt-5.5",
    "whisper-1", "text-embedding-3-small", "text-embedding-3-large",
    # Anthropic
    "claude-haiku-4-5", "claude-sonnet-4-5", "claude-opus-4-5",
    "claude-sonnet-4-6", "claude-opus-4-6", "claude-opus-4-7",
    # Google AI
    "gemini-flash-lite-latest", "gemini-flash-latest", "gemini-pro-latest",
    "gemini-3-flash-preview", "gemini-3-pro-image-preview", "gemini-3.1-flash-image-preview",
    # xAI
    "grok-4-1-fast-non-reasoning", "grok-4-1-fast-reasoning", "grok-4.20-non-reasoning", "grok-4.20-reasoning",
    "grok-imagine-image", "grok-imagine-image-pro",
    # Perplexity
    "sonar", "sonar-pro", "sonar-reasoning-pro", "sonar-deep-research",
    # Replicate
    "black-forest-labs/flux-1.1-pro", "black-forest-labs/flux-kontext-pro",
    "black-forest-labs/flux-2-pro", "black-forest-labs/flux-2-max",
    "openai/gpt-image-1.5", "openai/gpt-image-2",
    "bytedance/seedream-4", "bytedance/seedream-4.5",
    "google/nano-banana", "google/nano-banana-pro", "google/nano-banana-2",
    # API Integrations
    "currency-converter5.p.rapidapi.com", "x.api-v2-post.read", "v1.cryptocurrency.quotes.latest",
    # Internal
    "credit_transfer",
)

TOOL_CHOICE_COLUMNS: tuple[str, ...] = (
    "tool_choice_chat",
    "tool_choice_reasoning",
    "tool_choice_copywriting",
    "tool_choice_vision",
    "tool_choice_hearing",
    "tool_choice_images_gen",
    "tool_choice_images_edit",
    "tool_choice_search",
    "tool_choice_embedding",
    "tool_choice_api_fiat_exchange",
    "tool_choice_api_crypto_exchange",
    "tool_choice_api_twitter",
)


def upgrade() -> None:
    quoted_ids = ", ".join(f"'{id_}'" for id_ in SUPPORTED_MODEL_IDS)
    for column in TOOL_CHOICE_COLUMNS:
        op.execute(
            text(
                f"UPDATE simulants SET {column} = NULL "
                f"WHERE {column} IS NOT NULL AND {column} NOT IN ({quoted_ids})",
            ),
        )


def downgrade() -> None:
    # No-op: deprecated/removed model IDs were nulled out and cannot be restored.
    pass
