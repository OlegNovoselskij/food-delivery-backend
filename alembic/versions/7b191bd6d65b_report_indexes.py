"""report indexes

Revision ID: 7b191bd6d65b
Revises: 4a67f1e70e09
Create Date: 2026-10-11 17:12:23.499402

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7b191bd6d65b'
down_revision: Union[str, Sequence[str], None] = '4a67f1e70e09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_enrollments_course_status', 'enrollments', ['course_id', 'status'], unique=False)
    op.create_index('ix_payments_status_created', 'payments', ['status', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_payments_status_created', table_name='payments')
    op.drop_index('ix_enrollments_course_status', table_name='enrollments')
