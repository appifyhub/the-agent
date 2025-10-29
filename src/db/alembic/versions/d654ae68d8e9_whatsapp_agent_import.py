"""whatsapp_agent_import

Revision ID: d654ae68d8e9
Revises: 8619380f740f
Create Date: 2025-10-27 13:13:50.499386

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

from features.integrations.integration_config import THE_AGENT
from util.config import config

# revision identifiers, used by Alembic.
revision: str = "d654ae68d8e9"
down_revision: Union[str, None] = "8619380f740f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add WhatsApp fields to the existing Telegram agent (unified agent approach)
    assert THE_AGENT.whatsapp_phone_number is not None, "Agent phone number must be set"
    assert THE_AGENT.telegram_user_id is not None, "Agent telegram user ID must be set"

    encryption_key = config.token_encrypt_secret.get_secret_value()
    wa_phone_plaintext = THE_AGENT.whatsapp_phone_number.get_secret_value()

    # Update existing agent with WhatsApp fields
    op.execute(text("""
        UPDATE simulants
        SET
            whatsapp_user_id = :wa_user_id,
            whatsapp_phone_number = pgp_sym_encrypt(:wa_phone_number, :encryption_key)
        WHERE telegram_user_id = :telegram_user_id
        AND telegram_username = :telegram_username
    """).bindparams(
        wa_user_id = THE_AGENT.whatsapp_user_id,
        wa_phone_number = wa_phone_plaintext,
        encryption_key = encryption_key,
        telegram_user_id = THE_AGENT.telegram_user_id,
        telegram_username = THE_AGENT.telegram_username,
    ))


def downgrade() -> None:
    # Remove WhatsApp fields from the agent
    op.execute(text("""
        UPDATE simulants
        SET
            whatsapp_user_id = NULL,
            whatsapp_phone_number = NULL
        WHERE telegram_user_id = :telegram_user_id
        AND telegram_username = :telegram_username
    """).bindparams(
        telegram_user_id = THE_AGENT.telegram_user_id,
        telegram_username = THE_AGENT.telegram_username,
    ))
