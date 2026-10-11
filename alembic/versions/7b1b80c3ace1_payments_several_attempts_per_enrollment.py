"""payments: several attempts per enrollment

Revision ID: 7b1b80c3ace1
Revises: 1eda0ffae88d
Create Date: 2026-10-11 15:14:46.568422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7b1b80c3ace1'
down_revision: Union[str, Sequence[str], None] = '1eda0ffae88d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(op.f('payments_enrollment_id_key'), 'payments', type_='unique')
    op.create_index(op.f('ix_payments_enrollment_id'), 'payments', ['enrollment_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_payments_enrollment_id'), table_name='payments')
    op.create_unique_constraint(op.f('payments_enrollment_id_key'), 'payments', ['enrollment_id'], postgresql_nulls_not_distinct=False)
