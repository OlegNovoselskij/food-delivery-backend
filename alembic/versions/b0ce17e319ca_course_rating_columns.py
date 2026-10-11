"""course rating columns

Revision ID: b0ce17e319ca
Revises: 516541ee860d
Create Date: 2026-10-11 18:52:21.188419

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b0ce17e319ca'
down_revision: Union[str, Sequence[str], None] = '516541ee860d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('courses', sa.Column('rating_avg', sa.Numeric(precision=3, scale=2), nullable=True))
    op.add_column('courses', sa.Column('reviews_count', sa.Integer(), server_default='0', nullable=False))
    op.execute(
        "UPDATE courses SET rating_avg = r.avg_rating, reviews_count = r.cnt "
        "FROM (SELECT course_id, ROUND(AVG(rating), 2) AS avg_rating, COUNT(*) AS cnt FROM reviews GROUP BY course_id) r "
        "WHERE r.course_id = courses.id"
    )


def downgrade() -> None:
    op.drop_column('courses', 'reviews_count')
    op.drop_column('courses', 'rating_avg')
