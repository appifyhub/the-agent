"""whatsapp_support

Revision ID: 8619380f740f
Revises: 80a73d49a9a8
Create Date: 2025-10-15 13:55:26.588149

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import BYTEA

# revision identifiers, used by Alembic.
revision: str = "8619380f740f"
down_revision: Union[str, None] = "80a73d49a9a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add WhatsApp user columns
    op.add_column("simulants", sa.Column("whatsapp_user_id", sa.String(), nullable = True))
    op.add_column("simulants", sa.Column("whatsapp_phone_number", BYTEA, nullable = True))
    op.create_index(op.f("ix_simulants_whatsapp_user_id"), "simulants", ["whatsapp_user_id"], unique = True)

    # Add 'whatsapp' to ChatType enum
    # Convert column to text
    op.execute(text("""
        ALTER TABLE chat_configs
        ALTER COLUMN chat_type TYPE text
    """))

    # Drop the old enum type
    op.execute(text("DROP TYPE chattype CASCADE"))

    # Create new enum type with whatsapp added
    op.execute(text("""
        CREATE TYPE chattype AS ENUM ('telegram', 'whatsapp', 'github', 'background')
    """))

    # Convert column back to enum type
    op.execute(text("""
        ALTER TABLE chat_configs
        ALTER COLUMN chat_type TYPE chattype
        USING chat_type::chattype
    """))


def downgrade() -> None:
    # Revert ChatType enum (remove whatsapp)
    # Convert column to text
    op.execute(text("""
        ALTER TABLE chat_configs
        ALTER COLUMN chat_type TYPE text
    """))

    # Drop the enum type
    op.execute(text("DROP TYPE chattype CASCADE"))

    # Create enum type without whatsapp
    op.execute(text("""
        CREATE TYPE chattype AS ENUM ('telegram', 'github', 'background')
    """))

    # Convert column back to enum type
    op.execute(text("""
        ALTER TABLE chat_configs
        ALTER COLUMN chat_type TYPE chattype
        USING chat_type::chattype
    """))

    # Drop WhatsApp user columns
    op.drop_index(op.f("ix_simulants_whatsapp_user_id"), table_name = "simulants")
    op.drop_column("simulants", "whatsapp_phone_number")
    op.drop_column("simulants", "whatsapp_user_id")
