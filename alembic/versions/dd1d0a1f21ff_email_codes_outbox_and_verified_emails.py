"""email codes, outbox and verified emails

Revision ID: dd1d0a1f21ff
Revises: 7b191bd6d65b
Create Date: 2026-10-11 17:57:40.320602

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'dd1d0a1f21ff'
down_revision: Union[str, Sequence[str], None] = '7b191bd6d65b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('email_outbox',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('to_email', sa.String(), nullable=False),
    sa.Column('subject', sa.String(), nullable=False),
    sa.Column('text_body', sa.Text(), nullable=True),
    sa.Column('html_body', sa.Text(), nullable=True),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('next_attempt_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_error', sa.String(), nullable=True),
    sa.Column('dedupe_key', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('dedupe_key')
    )
    op.create_index('ix_email_outbox_due', 'email_outbox', ['status', 'next_attempt_at'], unique=False)
    op.create_table('email_codes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('purpose', sa.String(), nullable=False),
    sa.Column('code_hash', sa.String(), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'purpose', name='uq_email_code_user_purpose')
    )
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('users', sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE users SET email_verified = true WHERE password_hash IS NOT NULL")
    op.alter_column('users', 'password_hash',
               existing_type=sa.VARCHAR(),
               nullable=True)


def downgrade() -> None:
    op.alter_column('users', 'password_hash',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.drop_column('users', 'password_changed_at')
    op.drop_column('users', 'email_verified')
    op.drop_table('email_codes')
    op.drop_index('ix_email_outbox_due', table_name='email_outbox')
    op.drop_table('email_outbox')
