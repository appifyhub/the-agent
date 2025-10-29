"""ensure_whatsapp_agent_exists

Revision ID: 3f8b2e4c9a71
Revises: d654ae68d8e9
Create Date: 2025-10-29 01:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

from features.integrations.integration_config import THE_AGENT
from util.config import config

# revision identifiers, used by Alembic.
revision: str = "3f8b2e4c9a71"
down_revision: Union[str, None] = "d654ae68d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This migration ensures the agent exists with the correct ID and WhatsApp fields
    # Handles three scenarios:
    # 1. Production: agent exists with wrong ID (9e0c5a1a...) -> migrate messages, delete old, create correct
    # 2. Local/Staging: multiple agents exist -> migrate messages, delete duplicates, upsert correct one
    # 3. Fresh DB: agent doesn't exist -> create it
    # Idempotent: safe to run multiple times

    assert THE_AGENT.whatsapp_phone_number is not None, "Agent phone number must be set"
    assert THE_AGENT.telegram_user_id is not None, "Agent telegram user ID must be set"

    encryption_key = config.token_encrypt_secret.get_secret_value()
    wa_phone_plaintext = THE_AGENT.whatsapp_phone_number.get_secret_value()

    # Step 1: Migrate any chat messages from wrong agent ID to correct ID
    # This handles local/staging where messages reference the wrong agent
    op.execute(text("""
        UPDATE chat_messages
        SET author_id = :correct_id
        WHERE author_id IN (
            SELECT id FROM simulants
            WHERE telegram_user_id = :telegram_user_id
            AND id != :correct_id
        )
    """).bindparams(
        correct_id = str(THE_AGENT.id),
        telegram_user_id = THE_AGENT.telegram_user_id,
    ))

    # Step 2: Delete any agent with matching telegram_user_id but wrong ID
    # Now safe to delete since messages have been migrated
    op.execute(text("""
        DELETE FROM simulants
        WHERE telegram_user_id = :telegram_user_id
        AND id != :correct_id
    """).bindparams(
        correct_id = str(THE_AGENT.id),
        telegram_user_id = THE_AGENT.telegram_user_id,
    ))

    # Step 3: Upsert the agent with correct ID and all current fields
    # Insert if not exists, update if exists
    op.execute(text("""
        INSERT INTO simulants (
            id,
            full_name,
            "group",
            telegram_username,
            telegram_chat_id,
            telegram_user_id,
            whatsapp_user_id,
            whatsapp_phone_number,
            created_at
        )
        VALUES (
            :id,
            :full_name,
            :group,
            :telegram_username,
            :telegram_chat_id,
            :telegram_user_id,
            :whatsapp_user_id,
            pgp_sym_encrypt(:wa_phone_number, :encryption_key),
            :created_at
        )
        ON CONFLICT (id) DO UPDATE SET
            full_name = EXCLUDED.full_name,
            telegram_username = EXCLUDED.telegram_username,
            telegram_chat_id = EXCLUDED.telegram_chat_id,
            telegram_user_id = EXCLUDED.telegram_user_id,
            whatsapp_user_id = EXCLUDED.whatsapp_user_id,
            whatsapp_phone_number = EXCLUDED.whatsapp_phone_number
    """).bindparams(
        id = str(THE_AGENT.id),
        full_name = THE_AGENT.full_name,
        group = THE_AGENT.group.value,
        telegram_username = THE_AGENT.telegram_username,
        telegram_chat_id = THE_AGENT.telegram_chat_id,
        telegram_user_id = THE_AGENT.telegram_user_id,
        whatsapp_user_id = THE_AGENT.whatsapp_user_id,
        wa_phone_number = wa_phone_plaintext,
        encryption_key = encryption_key,
        created_at = "2024-01-01",
    ))


def downgrade() -> None:
    # No downgrade. We don't want to delete the agent in production.
    # Too risky - simply add a new migration.
    pass
