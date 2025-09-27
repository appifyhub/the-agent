"""multi_platform_chat_types

Revision ID: 80a73d49a9a8
Revises: 907f4ee4b4cf
Create Date: 2025-09-21 03:38:40.822866

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

from features.integrations.integration_config import BACKGROUND_AGENT, GITHUB_AGENT, TELEGRAM_AGENT

# revision identifiers, used by Alembic.
revision: str = "80a73d49a9a8"
down_revision: Union[str, None] = "907f4ee4b4cf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update ChatType enum to only have the new values
    # First, update any existing records that use old enum values to 'telegram'
    op.execute(text("""
        UPDATE chat_configs
        SET chat_type = 'telegram'
        WHERE chat_type IN ('standalone_web', 'standalone_app', 'extension_web', 'whatsapp')
    """))

    # Change column to text first
    op.execute(text("""
        ALTER TABLE chat_configs
        ALTER COLUMN chat_type TYPE text
    """))

    # Drop the old enum type
    op.execute(text("DROP TYPE chattype CASCADE"))

    # Create the new enum type with only the values we want
    op.execute(text("""
        CREATE TYPE chattype AS ENUM ('telegram', 'github', 'background')
    """))

    # Update the column to use the new enum type
    op.execute(text("""
        ALTER TABLE chat_configs
        ALTER COLUMN chat_type TYPE chattype
        USING chat_type::chattype
    """))

    # Insert the telegram agent if it doesn't exist
    op.execute(text("""
        INSERT INTO simulants (id, full_name, "group", telegram_username, telegram_chat_id, telegram_user_id, created_at)
        SELECT :id, :full_name, :group, :telegram_username, :telegram_chat_id, :telegram_user_id, :created_at
        WHERE NOT EXISTS (
            SELECT 1 FROM simulants WHERE id = :id
        )
    """).bindparams(
        id = str(TELEGRAM_AGENT.id),
        full_name = TELEGRAM_AGENT.full_name,
        group = TELEGRAM_AGENT.group.value,
        telegram_username = TELEGRAM_AGENT.telegram_username,
        telegram_chat_id = TELEGRAM_AGENT.telegram_chat_id,
        telegram_user_id = TELEGRAM_AGENT.telegram_user_id,
        created_at = "2024-01-01",  # Default date
    ))

    # Insert the background agent if it doesn't exist (copy all properties from telegram agent)
    op.execute(text("""
        INSERT INTO simulants (
            id, full_name, "group", telegram_username, telegram_chat_id, telegram_user_id,
            open_ai_key, anthropic_key, google_ai_key, perplexity_key, replicate_key,
            rapid_api_key, coinmarketcap_key, tool_choice_chat, tool_choice_reasoning,
            tool_choice_copywriting, tool_choice_vision, tool_choice_hearing,
            tool_choice_images_gen, tool_choice_images_edit, tool_choice_images_restoration,
            tool_choice_images_inpainting, tool_choice_images_background_removal,
            tool_choice_search, tool_choice_embedding, tool_choice_api_fiat_exchange,
            tool_choice_api_crypto_exchange, tool_choice_api_twitter, created_at
        )
        SELECT
            :bg_id, :bg_full_name, t.group, NULL, NULL, NULL,
            t.open_ai_key, t.anthropic_key, t.google_ai_key, t.perplexity_key, t.replicate_key,
            t.rapid_api_key, t.coinmarketcap_key, t.tool_choice_chat, t.tool_choice_reasoning,
            t.tool_choice_copywriting, t.tool_choice_vision, t.tool_choice_hearing,
            t.tool_choice_images_gen, t.tool_choice_images_edit, t.tool_choice_images_restoration,
            t.tool_choice_images_inpainting, t.tool_choice_images_background_removal,
            t.tool_choice_search, t.tool_choice_embedding, t.tool_choice_api_fiat_exchange,
            t.tool_choice_api_crypto_exchange, t.tool_choice_api_twitter, t.created_at
        FROM simulants t
        WHERE t.id = :tg_id
        AND NOT EXISTS (SELECT 1 FROM simulants WHERE id = :bg_id)
    """).bindparams(
        bg_id = str(BACKGROUND_AGENT.id),
        bg_full_name = BACKGROUND_AGENT.full_name,
        tg_id = str(TELEGRAM_AGENT.id),
    ))

    # Insert the github agent if it doesn't exist (copy all properties from telegram agent)
    op.execute(text("""
        INSERT INTO simulants (
            id, full_name, "group", telegram_username, telegram_chat_id, telegram_user_id,
            open_ai_key, anthropic_key, google_ai_key, perplexity_key, replicate_key,
            rapid_api_key, coinmarketcap_key, tool_choice_chat, tool_choice_reasoning,
            tool_choice_copywriting, tool_choice_vision, tool_choice_hearing,
            tool_choice_images_gen, tool_choice_images_edit, tool_choice_images_restoration,
            tool_choice_images_inpainting, tool_choice_images_background_removal,
            tool_choice_search, tool_choice_embedding, tool_choice_api_fiat_exchange,
            tool_choice_api_crypto_exchange, tool_choice_api_twitter, created_at
        )
        SELECT
            :gh_id, :gh_full_name, t.group, NULL, NULL, NULL,
            t.open_ai_key, t.anthropic_key, t.google_ai_key, t.perplexity_key, t.replicate_key,
            t.rapid_api_key, t.coinmarketcap_key, t.tool_choice_chat, t.tool_choice_reasoning,
            t.tool_choice_copywriting, t.tool_choice_vision, t.tool_choice_hearing,
            t.tool_choice_images_gen, t.tool_choice_images_edit, t.tool_choice_images_restoration,
            t.tool_choice_images_inpainting, t.tool_choice_images_background_removal,
            t.tool_choice_search, t.tool_choice_embedding, t.tool_choice_api_fiat_exchange,
            t.tool_choice_api_crypto_exchange, t.tool_choice_api_twitter, t.created_at
        FROM simulants t
        WHERE t.id = :tg_id
        AND NOT EXISTS (SELECT 1 FROM simulants WHERE id = :gh_id)
    """).bindparams(
        gh_id = str(GITHUB_AGENT.id),
        gh_full_name = GITHUB_AGENT.full_name,
        tg_id = str(TELEGRAM_AGENT.id),
    ))


def downgrade() -> None:
    # Revert ChatType enum to original values
    # Change column to text first
    op.execute(text("""
        ALTER TABLE chat_configs
        ALTER COLUMN chat_type TYPE text
    """))

    # Drop the new enum type
    op.execute(text("DROP TYPE chattype CASCADE"))

    # Recreate the original enum type with 5 values
    op.execute(text("""
        CREATE TYPE chattype AS ENUM ('standalone_web', 'standalone_app', 'extension_web', 'telegram', 'whatsapp')
    """))

    # Update the column to use the original enum type
    op.execute(text("""
        ALTER TABLE chat_configs
        ALTER COLUMN chat_type TYPE chattype
        USING chat_type::chattype
    """))
