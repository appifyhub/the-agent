"""per_chat_settings

Revision ID: a5d60e76f435
Revises: 284b0c3ee721
Create Date: 2026-05-02 21:49:50.104360

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# All known bot user IDs across all environments (staging + prod).
# Hard-coded to avoid coupling to config or integration_config (both change over time).
_BOT_IDS = [
    "4fee5e61-77af-5ada-97b0-3c5fe73827dc",  # THE_AGENT (all envs)
    "0035d8fb-5010-5cea-8de6-2a3573397753",  # BACKGROUND_AGENT (all envs)
    "b72db6ff-954a-5bdc-9991-3663022cec2e",  # legacy TELEGRAM_AGENT (staging orphan)
]

# revision identifiers, used by Alembic.
revision: str = "a5d60e76f435"
down_revision: Union[str, None] = "284b0c3ee721"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_memberships",
        sa.Column("user_id", sa.UUID(), nullable = False),
        sa.Column("chat_id", sa.UUID(), nullable = False),
        sa.Column("is_admin", sa.Boolean(), server_default = sa.text("false"), nullable = False),
        sa.Column("use_about_me", sa.Boolean(), server_default = sa.text("true"), nullable = False),
        sa.Column("use_custom_prompt", sa.Boolean(), server_default = sa.text("true"), nullable = False),
        sa.ForeignKeyConstraint(["chat_id"], ["chat_configs.chat_id"], name = "chat_memberships_chat_id_fkey"),
        sa.ForeignKeyConstraint(["user_id"], ["simulants.id"], name = "chat_memberships_user_id_fkey"),
        sa.PrimaryKeyConstraint("user_id", "chat_id", name = "pk_chat_membership"),
    )
    op.create_index("ix_chat_memberships_chat_id", "chat_memberships", ["chat_id"], unique = False)
    op.create_index("ix_chat_memberships_user_id", "chat_memberships", ["user_id"], unique = False)
    _bot_ids_sql = ", ".join(f"'{bid}'::uuid" for bid in _BOT_IDS)
    op.execute(sa.text(f"""
        DELETE FROM chat_memberships WHERE user_id = ANY(ARRAY[{_bot_ids_sql}])
    """))
    op.execute(sa.text(f"""
        INSERT INTO chat_memberships (user_id, chat_id, is_admin, use_about_me, use_custom_prompt)
        SELECT DISTINCT
            m.author_id,
            m.chat_id,
            CASE
                WHEN cc.is_private AND (
                    cc.external_id = s.telegram_chat_id OR
                    cc.external_id = s.whatsapp_user_id
                ) THEN true
                ELSE false
            END,
            true,
            true
        FROM chat_messages m
        JOIN simulants s ON s.id = m.author_id
        JOIN chat_configs cc ON cc.chat_id = m.chat_id
        WHERE m.author_id IS NOT NULL
        AND m.author_id != ALL(ARRAY[{_bot_ids_sql}])
        ON CONFLICT (user_id, chat_id) DO NOTHING
    """))
    op.drop_column("chat_configs", "use_about_me")
    op.drop_column("chat_configs", "use_custom_prompt")


def downgrade() -> None:
    # Per-user granularity (use_about_me, use_custom_prompt per membership) is lost on rollback —
    # the restored columns on chat_configs default to true for all users in that chat.
    op.add_column(
        "chat_configs",
        sa.Column("use_custom_prompt", sa.BOOLEAN(), server_default = sa.text("true"), autoincrement = False, nullable = False),
    )
    op.add_column(
        "chat_configs",
        sa.Column("use_about_me", sa.BOOLEAN(), server_default = sa.text("true"), autoincrement = False, nullable = False),
    )
    op.drop_index("ix_chat_memberships_user_id", table_name = "chat_memberships")
    op.drop_index("ix_chat_memberships_chat_id", table_name = "chat_memberships")
    op.drop_table("chat_memberships")
