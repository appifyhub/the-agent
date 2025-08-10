"""internal_chat_id

Revision ID: 4711ede6d1b3
Revises: 32e1f74679b4
Create Date: 2025-08-08 22:17:05.123862

"""
from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4711ede6d1b3"
down_revision: Union[str, None] = "32e1f74679b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1) Add external_id and backfill from old chat_id (which is currently external text id)
    op.add_column("chat_configs", sa.Column("external_id", sa.String(), nullable = True))
    conn.execute(sa.text("UPDATE chat_configs SET external_id = chat_id"))

    # 2) Add new UUID chat_id columns alongside existing ones
    op.add_column("chat_configs", sa.Column("new_chat_id", sa.UUID(), nullable = True))
    op.add_column("chat_messages", sa.Column("new_chat_id", sa.UUID(), nullable = True))
    op.add_column("chat_message_attachments", sa.Column("new_chat_id", sa.UUID(), nullable = True))
    op.add_column("price_alerts", sa.Column("new_chat_id", sa.UUID(), nullable = True))

    # 3) Generate UUIDs for chat_configs.new_chat_id (Python-side)
    rows = conn.execute(sa.text("SELECT chat_id FROM chat_configs")).fetchall()
    for (old_chat_id,) in rows:
        new_uuid = uuid.uuid4()
        conn.execute(
            sa.text("UPDATE chat_configs SET new_chat_id = :new WHERE chat_id = :old"),
            {"new": str(new_uuid), "old": old_chat_id},
        )

    # 4) Relink dependents by joining old text chat_id to chat_configs.external_id
    conn.execute(
        sa.text(
            """
            UPDATE chat_messages m
            SET new_chat_id = c.new_chat_id
            FROM chat_configs c
            WHERE m.chat_id = c.external_id
            """,
        ),
    )
    conn.execute(
        sa.text(
            """
            UPDATE chat_message_attachments a
            SET new_chat_id = c.new_chat_id
            FROM chat_configs c
            WHERE a.chat_id = c.external_id
            """,
        ),
    )
    conn.execute(
        sa.text(
            """
            UPDATE price_alerts p
            SET new_chat_id = c.new_chat_id
            FROM chat_configs c
            WHERE p.chat_id = c.external_id
            """,
        ),
    )

    # 5) Drop constraints that reference old chat_id
    op.drop_constraint("chat_messages_chat_id_fkey", "chat_messages", type_ = "foreignkey")
    # chat_message_attachments FK name was auto-generated in older migrations; drop possible legacy names if present
    conn.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'chat_message_attachments_message_fkey'
                ) THEN
                    ALTER TABLE chat_message_attachments DROP CONSTRAINT chat_message_attachments_message_fkey;
                END IF;
                IF EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'chat_message_attachments_chat_id_fkey'
                ) THEN
                    ALTER TABLE chat_message_attachments DROP CONSTRAINT chat_message_attachments_chat_id_fkey;
                END IF;
                IF EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'chat_message_attachments_chat_id_message_id_fkey'
                ) THEN
                    ALTER TABLE chat_message_attachments DROP CONSTRAINT chat_message_attachments_chat_id_message_id_fkey;
                END IF;
            END $$;
            """,
        ),
    )
    op.drop_constraint("price_alerts_chat_id_fkey", "price_alerts", type_ = "foreignkey")
    # Drop PK with CASCADE to remove dependent index constraints
    conn.execute(sa.text("ALTER TABLE chat_messages DROP CONSTRAINT pk_chat_message CASCADE"))
    op.drop_constraint("pk_price_alert", "price_alerts", type_ = "primary")
    # chat_configs had default PK name
    op.drop_constraint("chat_configs_pkey", "chat_configs", type_ = "primary")
    # Drop also the old unique that references old chat_id (will recreate after swap)
    op.drop_constraint("uq_message_per_chat", "chat_messages", type_ = "unique")

    # 6) Swap columns: drop old chat_id (text), rename new_chat_id -> chat_id (uuid)
    op.drop_column("chat_messages", "chat_id")
    op.drop_column("chat_message_attachments", "chat_id")
    op.drop_column("price_alerts", "chat_id")
    op.drop_column("chat_configs", "chat_id")

    op.alter_column(
        "chat_configs",
        "new_chat_id",
        new_column_name = "chat_id",
        existing_type = sa.UUID(),
        nullable = False,
    )
    op.alter_column(
        "chat_messages",
        "new_chat_id",
        new_column_name = "chat_id",
        existing_type = sa.UUID(),
        nullable = False,
    )
    op.alter_column(
        "chat_message_attachments",
        "new_chat_id",
        new_column_name = "chat_id",
        existing_type = sa.UUID(),
        nullable = False,
    )
    op.alter_column(
        "price_alerts",
        "new_chat_id",
        new_column_name = "chat_id",
        existing_type = sa.UUID(),
        nullable = False,
    )

    # 7) Recreate PKs and FKs on new UUID chat_id
    op.create_primary_key("chat_configs_pkey", "chat_configs", ["chat_id"])
    op.create_primary_key("pk_chat_message", "chat_messages", ["chat_id", "message_id"])
    op.create_primary_key("pk_price_alert", "price_alerts", ["chat_id", "base_currency", "desired_currency"])

    op.create_unique_constraint("uq_message_per_chat", "chat_messages", ["chat_id", "message_id"])

    op.create_foreign_key(
        "chat_messages_chat_id_fkey",
        "chat_messages",
        "chat_configs",
        ["chat_id"],
        ["chat_id"],
    )
    op.create_foreign_key(
        "chat_message_attachments_message_fkey",
        "chat_message_attachments",
        "chat_messages",
        ["chat_id", "message_id"],
        ["chat_id", "message_id"],
    )
    op.create_foreign_key(
        "price_alerts_chat_id_fkey",
        "price_alerts",
        "chat_configs",
        ["chat_id"],
        ["chat_id"],
    )

    # 8) Ensure unique composite for lookups by platform identifiers
    op.create_index(
        "uq_chat_configs_external_id_type",
        "chat_configs",
        ["external_id", "chat_type"],
        unique = True,
        postgresql_where = sa.text("external_id IS NOT NULL"),
    )


def downgrade() -> None:
    conn = op.get_bind()

    # 1) Drop unique index
    op.drop_index("uq_chat_configs_external_id_type", table_name = "chat_configs")

    # 2) Add legacy text chat_id columns back
    op.add_column("chat_configs", sa.Column("old_chat_id", sa.String(), nullable = True))
    op.add_column("chat_messages", sa.Column("old_chat_id", sa.String(), nullable = True))
    op.add_column("chat_message_attachments", sa.Column("old_chat_id", sa.String(), nullable = True))
    op.add_column("price_alerts", sa.Column("old_chat_id", sa.String(), nullable = True))

    # 3) Backfill old_chat_id from external_id via joins on current UUID chat_id
    conn.execute(
        sa.text(
            """
            UPDATE chat_configs SET old_chat_id = external_id
            """,
        ),
    )
    conn.execute(
        sa.text(
            """
            UPDATE chat_messages m
            SET old_chat_id = c.external_id
            FROM chat_configs c
            WHERE m.chat_id = c.chat_id
            """,
        ),
    )
    conn.execute(
        sa.text(
            """
            UPDATE chat_message_attachments a
            SET old_chat_id = c.external_id
            FROM chat_configs c
            WHERE a.chat_id = c.chat_id
            """,
        ),
    )
    conn.execute(
        sa.text(
            """
            UPDATE price_alerts p
            SET old_chat_id = c.external_id
            FROM chat_configs c
            WHERE p.chat_id = c.chat_id
            """,
        ),
    )

    # 4) Drop FKs/PKs/uniques that reference UUID chat_id
    op.drop_constraint("chat_message_attachments_message_fkey", "chat_message_attachments", type_ = "foreignkey")
    op.drop_constraint("chat_messages_chat_id_fkey", "chat_messages", type_ = "foreignkey")
    op.drop_constraint("price_alerts_chat_id_fkey", "price_alerts", type_ = "foreignkey")
    op.drop_constraint("uq_message_per_chat", "chat_messages", type_ = "unique")
    op.drop_constraint("pk_price_alert", "price_alerts", type_ = "primary")
    op.drop_constraint("pk_chat_message", "chat_messages", type_ = "primary")
    op.drop_constraint("chat_configs_pkey", "chat_configs", type_ = "primary")

    # 5) Swap back: drop UUID chat_id, rename old_chat_id -> chat_id (text)
    op.drop_column("price_alerts", "chat_id")
    op.drop_column("chat_message_attachments", "chat_id")
    op.drop_column("chat_messages", "chat_id")
    op.drop_column("chat_configs", "chat_id")

    op.alter_column(
        "chat_configs",
        "old_chat_id",
        new_column_name = "chat_id",
        existing_type = sa.String(),
        nullable = False,
    )
    op.alter_column(
        "chat_messages",
        "old_chat_id",
        new_column_name = "chat_id",
        existing_type = sa.String(),
        nullable = False,
    )
    op.alter_column(
        "chat_message_attachments",
        "old_chat_id",
        new_column_name = "chat_id",
        existing_type = sa.String(),
        nullable = False,
    )
    op.alter_column(
        "price_alerts",
        "old_chat_id",
        new_column_name = "chat_id",
        existing_type = sa.String(),
        nullable = False,
    )

    # 6) Recreate PKs/uniques/FKs against text chat_id
    op.create_primary_key("chat_configs_pkey", "chat_configs", ["chat_id"])
    op.create_primary_key("pk_chat_message", "chat_messages", ["chat_id", "message_id"])
    op.create_unique_constraint("uq_message_per_chat", "chat_messages", ["chat_id", "message_id"])
    op.create_primary_key("pk_price_alert", "price_alerts", ["chat_id", "base_currency", "desired_currency"])

    op.create_foreign_key(
        "chat_messages_chat_id_fkey",
        "chat_messages",
        "chat_configs",
        ["chat_id"],
        ["chat_id"],
    )
    op.create_foreign_key(
        "chat_message_attachments_message_fkey",
        "chat_message_attachments",
        "chat_messages",
        ["chat_id", "message_id"],
        ["chat_id", "message_id"],
    )
    op.create_foreign_key(
        "price_alerts_chat_id_fkey",
        "price_alerts",
        "chat_configs",
        ["chat_id"],
        ["chat_id"],
    )

    # 7) Drop external_id (it did not exist prior to this migration)
    op.drop_column("chat_configs", "external_id")
