"""user_multi_provider_tokens

Revision ID: 541b08819f2d
Revises: 2969eb167237
Create Date: 2025-06-22 21:21:54.009014

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "541b08819f2d"
down_revision: Union[str, None] = "2969eb167237"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("simulants", sa.Column("anthropic_key", sa.String(), nullable = True))
    op.add_column("simulants", sa.Column("perplexity_key", sa.String(), nullable = True))
    op.add_column("simulants", sa.Column("replicate_key", sa.String(), nullable = True))
    op.add_column("simulants", sa.Column("rapid_api_key", sa.String(), nullable = True))
    op.add_column("simulants", sa.Column("coinmarketcap_key", sa.String(), nullable = True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("simulants", "coinmarketcap_key")
    op.drop_column("simulants", "rapid_api_key")
    op.drop_column("simulants", "replicate_key")
    op.drop_column("simulants", "perplexity_key")
    op.drop_column("simulants", "anthropic_key")
    # ### end Alembic commands ###
