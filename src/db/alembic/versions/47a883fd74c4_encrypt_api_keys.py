"""encrypt_api_keys

Revision ID: 47a883fd74c4
Revises: 0bbfd2411b29
Create Date: 2025-08-01 21:12:01.320547

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import BYTEA

from util.config import config

# revision identifiers, used by Alembic.
revision: str = "47a883fd74c4"
down_revision: Union[str, None] = "0bbfd2411b29"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if we're using PostgreSQL
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        raise Exception("This migration requires PostgreSQL. Current database: " + connection.dialect.name)

    # Enable pgcrypto extension
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))

    # Get encryption key
    encryption_key = config.token_encrypt_secret.get_secret_value()

    # Store API key fields to migrate
    api_key_fields = [
        "open_ai_key", "anthropic_key", "google_ai_key", "perplexity_key",
        "replicate_key", "rapid_api_key", "coinmarketcap_key",
    ]

    # First, add new encrypted columns as BYTEA
    for field in api_key_fields:
        op.add_column("simulants", sa.Column(f"{field}_encrypted", BYTEA, nullable = True))

    # Migrate existing data: encrypt non-null values
    for field in api_key_fields:
        connection.execute(text(f"""
            UPDATE simulants
            SET {field}_encrypted = pgp_sym_encrypt({field}, :key)
            WHERE {field} IS NOT NULL
        """), {"key": encryption_key})

    # Drop old VARCHAR columns
    for field in api_key_fields:
        op.drop_column("simulants", field)

    # Rename encrypted columns to original names
    for field in api_key_fields:
        op.alter_column("simulants", f"{field}_encrypted", new_column_name = field)

    # ### end Alembic commands ###


def downgrade() -> None:
    # Get encryption key
    encryption_key = config.token_encrypt_secret.get_secret_value()
    connection = op.get_bind()

    # Store API key fields to migrate back
    api_key_fields = [
        "open_ai_key", "anthropic_key", "google_ai_key", "perplexity_key",
        "replicate_key", "rapid_api_key", "coinmarketcap_key",
    ]

    # Add temporary VARCHAR columns
    for field in api_key_fields:
        op.add_column("simulants", sa.Column(f"{field}_decrypted", sa.VARCHAR(), nullable = True))

    # Decrypt existing data back to plaintext
    for field in api_key_fields:
        connection.execute(text(f"""
            UPDATE simulants
            SET {field}_decrypted = pgp_sym_decrypt({field}, :key)
            WHERE {field} IS NOT NULL
        """), {"key": encryption_key})

    # Drop encrypted BYTEA columns
    for field in api_key_fields:
        op.drop_column("simulants", field)

    # Rename decrypted columns back to original names
    for field in api_key_fields:
        op.alter_column("simulants", f"{field}_decrypted", new_column_name = field)

    # ### end Alembic commands ###
