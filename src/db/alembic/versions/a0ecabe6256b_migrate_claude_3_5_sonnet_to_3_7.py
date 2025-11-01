"""migrate_claude_3_5_sonnet_to_3_7

Revision ID: a0ecabe6256b
Revises: 7a9c3e5f2b1d
Create Date: 2025-11-01 01:42:21.216760

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "a0ecabe6256b"
down_revision: Union[str, None] = "7a9c3e5f2b1d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Migrate all tool_choice_* fields from claude-3-5-sonnet-latest to claude-3-7-sonnet-latest
    # Claude 3.5 Sonnet was removed from API, so we migrate users to Claude 3.7 Sonnet
    tool_choice_columns = [
        "tool_choice_chat",
        "tool_choice_reasoning",
        "tool_choice_copywriting",
        "tool_choice_vision",
        "tool_choice_hearing",
        "tool_choice_images_gen",
        "tool_choice_images_edit",
        "tool_choice_images_restoration",
        "tool_choice_images_inpainting",
        "tool_choice_images_background_removal",
        "tool_choice_search",
        "tool_choice_embedding",
        "tool_choice_api_fiat_exchange",
        "tool_choice_api_crypto_exchange",
        "tool_choice_api_twitter",
    ]

    for column in tool_choice_columns:
        op.execute(text(f"""
            UPDATE simulants
            SET {column} = 'claude-3-7-sonnet-latest'
            WHERE {column} = 'claude-3-5-sonnet-latest'
        """))


def downgrade() -> None:
    # Revert migration: move users back from claude-3-7-sonnet-latest to claude-3-5-sonnet-latest
    tool_choice_columns = [
        "tool_choice_chat",
        "tool_choice_reasoning",
        "tool_choice_copywriting",
        "tool_choice_vision",
        "tool_choice_hearing",
        "tool_choice_images_gen",
        "tool_choice_images_edit",
        "tool_choice_images_restoration",
        "tool_choice_images_inpainting",
        "tool_choice_images_background_removal",
        "tool_choice_search",
        "tool_choice_embedding",
        "tool_choice_api_fiat_exchange",
        "tool_choice_api_crypto_exchange",
        "tool_choice_api_twitter",
    ]

    for column in tool_choice_columns:
        op.execute(text(f"""
            UPDATE simulants
            SET {column} = 'claude-3-5-sonnet-latest'
            WHERE {column} = 'claude-3-7-sonnet-latest'
        """))
