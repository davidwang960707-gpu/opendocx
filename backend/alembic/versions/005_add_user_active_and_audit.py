"""add user is_active + last_login_at + audit_logs table

Revision ID: 005
Revises: 004
Create Date: 2026-06-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # P1-W3-A1: users 表加 is_active (软删标志) + last_login_at
    op.add_column(
        'users',
        sa.Column(
            'is_active',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
        ),
    )
    op.add_column(
        'users',
        sa.Column(
            'last_login_at',
            sa.DateTime(),
            nullable=True,
        ),
    )

    # P1-W3-A1: audit_logs 表
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('actor_id', sa.String(36), nullable=False, index=True),
        sa.Column('actor_email', sa.String(255), nullable=False),
        sa.Column('action', sa.String(50), nullable=False, index=True),
        sa.Column('target_type', sa.String(50), nullable=True, index=True),
        sa.Column('target_id', sa.String(36), nullable=True, index=True),
        sa.Column('payload', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'is_active')
