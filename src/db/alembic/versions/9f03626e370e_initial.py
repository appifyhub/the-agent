"""Initial

Revision ID: 9f03626e370e
Revises:
Create Date: 2024-05-19 20:04:32.674268

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f03626e370e"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "chat_configs",
        sa.Column("chat_id", sa.String(), nullable = False),
        sa.Column("persona_code", sa.String(), nullable = False),
        sa.Column("persona_name", sa.String(), nullable = False),
        sa.Column("language_iso_code", sa.String(), nullable = False),
        sa.Column("language_name", sa.String(), nullable = False),
        sa.PrimaryKeyConstraint("chat_id"),
    )
    op.create_table(
        "simulants",
        sa.Column("id", sa.UUID(), nullable = False),
        sa.Column("full_name", sa.String(), nullable = True),
        sa.Column("telegram_username", sa.String(), nullable = True),
        sa.Column("telegram_chat_id", sa.String(), nullable = True),
        sa.Column("open_ai_key", sa.String(), nullable = True),
        sa.Column("group", sa.Enum("standard", "beta", "alpha", "developer", name = "group"), nullable = False),
        sa.Column("created_at", sa.Date(), nullable = True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_simulants_telegram_chat_id"), "simulants", ["telegram_chat_id"], unique = True)
    op.create_index(op.f("ix_simulants_telegram_username"), "simulants", ["telegram_username"], unique = True)
    op.create_table(
        "chat_history",
        sa.Column("chat_id", sa.String(), nullable = False),
        sa.Column("message_id", sa.String(), nullable = False),
        sa.Column("author_name", sa.String(), nullable = True),
        sa.Column("author_username", sa.String(), nullable = True),
        sa.Column("sent_at", sa.DateTime(), nullable = False),
        sa.Column("text", sa.Text(), nullable = False),
        sa.ForeignKeyConstraint(["chat_id"], ["chat_configs.chat_id"]),
        sa.PrimaryKeyConstraint("chat_id", "message_id", name = "pk_chat_message"),
        sa.UniqueConstraint("chat_id", "message_id", name = "uq_message_per_chat"),
    )
    op.create_unique_constraint("uq_message_per_chat", "chat_history", ["chat_id", "message_id"])
    op.create_table(
        "invites",
        sa.Column("id", sa.UUID(), nullable = False),
        sa.Column("sender_id", sa.UUID(), nullable = False),
        sa.Column("receiver_id", sa.UUID(), nullable = False),
        sa.Column("invited_at", sa.DateTime(), nullable = False),
        sa.Column("accepted_at", sa.DateTime(), nullable = True),
        sa.ForeignKeyConstraint(["receiver_id"], ["simulants.id"]),
        sa.ForeignKeyConstraint(["sender_id"], ["simulants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("invites")
    op.drop_constraint("uq_message_per_chat", "chat_history", type_ = "unique")
    op.drop_table("chat_history")
    op.drop_index(op.f("ix_simulants_telegram_username"), table_name = "simulants")
    op.drop_index(op.f("ix_simulants_telegram_chat_id"), table_name = "simulants")
    op.drop_table("simulants")
    op.drop_table("chat_configs")
    # ### end Alembic commands ###
