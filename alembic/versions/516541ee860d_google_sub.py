"""google sub

Revision ID: 516541ee860d
Revises: dd1d0a1f21ff
Create Date: 2026-10-11 18:19:34.444573

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '516541ee860d'
down_revision: Union[str, Sequence[str], None] = 'dd1d0a1f21ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('google_sub', sa.String(), nullable=True))
    op.create_unique_constraint(None, 'users', ['google_sub'])


def downgrade() -> None:
    # WARNING: constraint name is None; this directive will fail as
    # rendered.  Add a name, or use a naming convention; see
    # https://alembic.sqlalchemy.org/en/latest/naming.html
    op.drop_constraint(None, 'users', type_='unique')
    op.drop_column('users', 'google_sub')
