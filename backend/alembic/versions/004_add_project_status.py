"""add project status column (active/paused/draft/archived)

Revision ID: 004
Revises: 003
Create Date: 2026-06-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # P1-W2-P2: 项目状态枚举 (active 活跃 / paused 暂停 / draft 草稿 / archived 归档)
    op.add_column(
        'projects',
        sa.Column(
            'status',
            sa.String(20),
            nullable=False,
            server_default='active',
        ),
    )
    # 给老项目回填 (1.0 都是 active)
    op.execute("UPDATE projects SET status = 'active' WHERE status IS NULL")


def downgrade() -> None:
    op.drop_column('projects', 'status')
