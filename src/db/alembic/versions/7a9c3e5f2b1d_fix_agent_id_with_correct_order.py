"""fix_agent_id_with_correct_order

Revision ID: 7a9c3e5f2b1d
Revises: d654ae68d8e9
Create Date: 2025-10-29 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

from features.integrations.integration_config import THE_AGENT
from util.config import config

# revision identifiers, used by Alembic.
revision: str = "7a9c3e5f2b1d"
down_revision: Union[str, None] = "d654ae68d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This migration ensures the agent exists with the correct ID and WhatsApp fields
    # Order matters:
    # 1. Create/upsert correct agent FIRST (must exist before messages can reference it)
    # 2. Migrate messages from wrong agent -> correct agent (safe now)
    # 3. Delete wrong agent (safe because messages no longer reference it)
    # Idempotent: safe to run multiple times

    assert THE_AGENT.whatsapp_phone_number is not None, "Agent phone number must be set"
    assert THE_AGENT.telegram_user_id is not None, "Agent telegram user ID must be set"

    encryption_key = config.token_encrypt_secret.get_secret_value()
    wa_phone_plaintext = THE_AGENT.whatsapp_phone_number.get_secret_value()

    # Temporarily drop foreign key constraints to allow ID updates
    # This is necessary because we may need to change the agent's primary key
    op.execute(text("ALTER TABLE chat_messages DROP CONSTRAINT IF EXISTS chat_messages_author_id_fkey"))
    op.execute(text("ALTER TABLE price_alerts DROP CONSTRAINT IF EXISTS price_alerts_owner_id_fkey"))
    op.execute(text("ALTER TABLE sponsorships DROP CONSTRAINT IF EXISTS sponsorships_sponsor_id_fkey"))
    op.execute(text("ALTER TABLE sponsorships DROP CONSTRAINT IF EXISTS sponsorships_receiver_id_fkey"))

    # Step 1: Migrate messages from wrong agent ID to correct ID (before agent exists)
    # Safe because FK constraint is temporarily dropped
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
    # Safe now because messages no longer reference it
    op.execute(text("""
        DELETE FROM simulants
        WHERE telegram_user_id = :telegram_user_id
        AND id != :correct_id
    """).bindparams(
        correct_id = str(THE_AGENT.id),
        telegram_user_id = THE_AGENT.telegram_user_id,
    ))

    # Step 3: Insert correct agent (or update if somehow already exists)
    # Safe now because no unique constraint conflicts
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

    # Re-add foreign key constraints
    op.execute(text("""
        ALTER TABLE chat_messages
        ADD CONSTRAINT chat_messages_author_id_fkey
        FOREIGN KEY (author_id) REFERENCES simulants(id)
    """))
    op.execute(text("""
        ALTER TABLE price_alerts
        ADD CONSTRAINT price_alerts_owner_id_fkey
        FOREIGN KEY (owner_id) REFERENCES simulants(id)
    """))
    op.execute(text("""
        ALTER TABLE sponsorships
        ADD CONSTRAINT sponsorships_sponsor_id_fkey
        FOREIGN KEY (sponsor_id) REFERENCES simulants(id)
    """))
    op.execute(text("""
        ALTER TABLE sponsorships
        ADD CONSTRAINT sponsorships_receiver_id_fkey
        FOREIGN KEY (receiver_id) REFERENCES simulants(id)
    """))


def downgrade() -> None:
    # No downgrade - we don't want to delete the agent in production
    pass
