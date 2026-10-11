"""quiz settings and attempt answers

Revision ID: 7f1ab2565ce6
Revises: 7b1b80c3ace1
Create Date: 2026-10-11 15:45:41.359953

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '7f1ab2565ce6'
down_revision: Union[str, Sequence[str], None] = '7b1b80c3ace1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('attempt_answers', sa.Column('selected_option_ids', postgresql.ARRAY(sa.Integer()), nullable=False))
    op.add_column('attempt_answers', sa.Column('teacher_comment', sa.Text(), nullable=True))
    op.create_unique_constraint('uq_attempt_question', 'attempt_answers', ['attempt_id', 'question_id'])
    op.drop_constraint(op.f('attempt_answers_selected_option_id_fkey'), 'attempt_answers', type_='foreignkey')
    op.drop_column('attempt_answers', 'selected_option_id')
    op.add_column('questions', sa.Column('explanation', sa.Text(), nullable=True))
    op.add_column('quiz_attempts', sa.Column('points_earned', sa.Integer(), nullable=True))
    op.add_column('quiz_attempts', sa.Column('points_total', sa.Integer(), nullable=True))
    op.add_column('quizzes', sa.Column('max_attempts', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('quizzes', 'max_attempts')
    op.drop_column('quiz_attempts', 'points_total')
    op.drop_column('quiz_attempts', 'points_earned')
    op.drop_column('questions', 'explanation')
    op.add_column('attempt_answers', sa.Column('selected_option_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key(op.f('attempt_answers_selected_option_id_fkey'), 'attempt_answers', 'answer_options', ['selected_option_id'], ['id'], ondelete='SET NULL')
    op.drop_constraint('uq_attempt_question', 'attempt_answers', type_='unique')
    op.drop_column('attempt_answers', 'teacher_comment')
    op.drop_column('attempt_answers', 'selected_option_ids')
