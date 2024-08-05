"""remove_personas

Revision ID: a89b3d0f78d1
Revises: 36c73da185ec
Create Date: 2024-08-05 13:51:00.295068

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a89b3d0f78d1'
down_revision: Union[str, None] = '36c73da185ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('chat_configs', 'persona_name')
    op.drop_column('chat_configs', 'persona_code')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('chat_configs', sa.Column('persona_code', sa.VARCHAR(), autoincrement = False, nullable = True))
    op.add_column('chat_configs', sa.Column('persona_name', sa.VARCHAR(), autoincrement = False, nullable = True))
    # ### end Alembic commands ###
