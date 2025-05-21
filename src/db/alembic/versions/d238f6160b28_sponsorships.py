"""sponsorships

Revision ID: d238f6160b28
Revises: 9d2363ca98db
Create Date: 2025-05-20 21:36:02.779308

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d238f6160b28"
down_revision: Union[str, None] = "9d2363ca98db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename table
    op.rename_table("invites", "sponsorships")
    # Rename columns
    op.alter_column("sponsorships", "sender_id", new_column_name = "sponsor_id")
    op.alter_column("sponsorships", "invited_at", new_column_name = "sponsored_at")


def downgrade() -> None:
    # Revert column names
    op.alter_column("sponsorships", "sponsor_id", new_column_name = "sender_id")
    op.alter_column("sponsorships", "sponsored_at", new_column_name = "invited_at")
    # Rename table back
    op.rename_table("sponsorships", "invites")
