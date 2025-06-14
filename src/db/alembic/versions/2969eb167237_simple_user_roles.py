"""simple_user_roles

Revision ID: 2969eb167237
Revises: d238f6160b28
Create Date: 2025-06-14 14:17:00.315779

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2969eb167237'
down_revision: Union[str, None] = 'd238f6160b28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # first convert all 'alpha' and 'beta' users to 'standard'
    op.execute("UPDATE simulants SET \"group\" = 'standard' WHERE \"group\" IN ('alpha', 'beta')")

    # then we update the constraints
    op.execute("CREATE TYPE group_new AS ENUM ('standard', 'developer')")
    op.execute("ALTER TABLE simulants ALTER COLUMN \"group\" TYPE group_new USING \"group\"::text::group_new")

    # and  then clean up types
    op.execute("DROP TYPE \"group\"")
    op.execute("ALTER TYPE group_new RENAME TO \"group\"")


def downgrade() -> None:
    # first we create the old enum type again and update constraints
    op.execute("CREATE TYPE group_new AS ENUM ('standard', 'beta', 'alpha', 'developer')")
    op.execute("ALTER TABLE simulants ALTER COLUMN \"group\" TYPE group_new USING \"group\"::text::group_new")

    # and then clean up types
    op.execute("DROP TYPE \"group\"")
    op.execute("ALTER TYPE group_new RENAME TO \"group\"")
