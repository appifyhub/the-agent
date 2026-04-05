"""custom_prompt

Revision ID: d05869c0af54
Revises: f81c0b60d07e
Create Date: 2026-04-05 15:31:38.901956

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import BYTEA

# revision identifiers, used by Alembic.
revision: str = "d05869c0af54"
down_revision: Union[str, None] = "f81c0b60d07e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_configs",
        sa.Column(
            "use_custom_prompt",
            sa.Boolean(),
            server_default = sa.text("true"),
            nullable = False,
        ),
    )
    op.add_column("simulants", sa.Column("custom_prompt", BYTEA, nullable = True))


def downgrade() -> None:
    op.drop_column("simulants", "custom_prompt")
    op.drop_column("chat_configs", "use_custom_prompt")
