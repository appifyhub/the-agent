"""encrypted_messages

Revision ID: 4a9e7ab95bf7
Revises: 4f143993b73f
Create Date: 2026-03-24 23:24:40.014105

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import BYTEA

from util.config import config

# revision identifiers, used by Alembic.
revision: str = "4a9e7ab95bf7"
down_revision: Union[str, None] = "4f143993b73f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        raise Exception("This migration requires PostgreSQL. Current database: " + connection.dialect.name)

    connection.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))

    encryption_key = config.token_encrypt_secret.get_secret_value()

    op.add_column("chat_messages", sa.Column("text_encrypted", BYTEA, nullable = True))

    connection.execute(text("""
        UPDATE chat_messages
        SET text_encrypted = pgp_sym_encrypt(text, :key)
        WHERE text IS NOT NULL
    """), {"key": encryption_key})

    op.drop_column("chat_messages", "text")
    op.alter_column("chat_messages", "text_encrypted", new_column_name = "text")

    # ### end Alembic commands ###


def downgrade() -> None:
    encryption_key = config.token_encrypt_secret.get_secret_value()
    connection = op.get_bind()

    op.add_column("chat_messages", sa.Column("text_decrypted", sa.VARCHAR(), nullable = True))

    connection.execute(text("""
        UPDATE chat_messages
        SET text_decrypted = pgp_sym_decrypt(text, :key)
        WHERE text IS NOT NULL
    """), {"key": encryption_key})

    op.drop_column("chat_messages", "text")
    op.alter_column("chat_messages", "text_decrypted", new_column_name = "text")

    # ### end Alembic commands ###
