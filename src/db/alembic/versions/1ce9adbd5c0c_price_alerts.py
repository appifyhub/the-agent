"""price-alerts

Revision ID: 1ce9adbd5c0c
Revises: 43a9b13811e6
Create Date: 2024-08-28 21:45:14.837390

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1ce9adbd5c0c'
down_revision: Union[str, None] = '43a9b13811e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'price_alerts',
        sa.Column('chat_id', sa.String(), nullable = False),
        sa.Column('base_currency', sa.String(), nullable = False),
        sa.Column('desired_currency', sa.String(), nullable = False),
        sa.Column('threshold_percent', sa.Integer(), nullable = False),
        sa.Column('last_price', sa.Float(), nullable = False),
        sa.Column('last_price_time', sa.DateTime(), nullable = False),
        sa.ForeignKeyConstraint(['chat_id'], ['chat_configs.chat_id']),
        sa.PrimaryKeyConstraint('chat_id', 'base_currency', 'desired_currency', name = 'pk_price_alert'),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('price_alerts')
    # ### end Alembic commands ###
