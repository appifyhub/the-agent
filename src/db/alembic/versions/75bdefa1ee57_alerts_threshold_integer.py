"""alerts-threshold-integer

Revision ID: 75bdefa1ee57
Revises: 1ce9adbd5c0c
Create Date: 2024-08-28 21:54:47.970086

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '75bdefa1ee57'
down_revision: Union[str, None] = '1ce9adbd5c0c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        'price_alerts', 'threshold_percent',
        existing_type = sa.DOUBLE_PRECISION(precision = 53),
        type_ = sa.Integer(),
        existing_nullable = False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        'price_alerts', 'threshold_percent',
        existing_type = sa.Integer(),
        type_ = sa.DOUBLE_PRECISION(precision = 53),
        existing_nullable = False,
    )
    # ### end Alembic commands ###
