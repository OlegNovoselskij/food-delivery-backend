"""drop pending_video_key

Revision ID: 1eda0ffae88d
Revises: c0120fb45e7b
Create Date: 2026-10-11 14:24:03.692137

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1eda0ffae88d'
down_revision: Union[str, Sequence[str], None] = 'c0120fb45e7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('lessons', 'pending_video_key')


def downgrade() -> None:
    op.add_column('lessons', sa.Column('pending_video_key', sa.VARCHAR(), autoincrement=False, nullable=True))
