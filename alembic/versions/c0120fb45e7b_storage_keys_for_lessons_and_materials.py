"""storage keys for lessons and materials

Revision ID: c0120fb45e7b
Revises: d30e62d5c2ce
Create Date: 2026-10-11 13:49:27.700375

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c0120fb45e7b'
down_revision: Union[str, Sequence[str], None] = 'd30e62d5c2ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('lesson_materials', sa.Column('file_key', sa.String(), nullable=False))
    op.add_column('lesson_materials', sa.Column('original_filename', sa.String(), nullable=False))
    op.add_column('lesson_materials', sa.Column('content_type', sa.String(), nullable=True))
    op.add_column('lesson_materials', sa.Column('size_bytes', sa.BigInteger(), nullable=True))
    op.drop_column('lesson_materials', 'file_url')
    op.add_column('lessons', sa.Column('video_key', sa.String(), nullable=True))
    op.add_column('lessons', sa.Column('pending_video_key', sa.String(), nullable=True))
    op.add_column('lessons', sa.Column('video_size', sa.BigInteger(), nullable=True))
    op.drop_column('lessons', 'video_url')


def downgrade() -> None:
    op.add_column('lessons', sa.Column('video_url', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_column('lessons', 'video_size')
    op.drop_column('lessons', 'pending_video_key')
    op.drop_column('lessons', 'video_key')
    op.add_column('lesson_materials', sa.Column('file_url', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.drop_column('lesson_materials', 'size_bytes')
    op.drop_column('lesson_materials', 'content_type')
    op.drop_column('lesson_materials', 'original_filename')
    op.drop_column('lesson_materials', 'file_key')
