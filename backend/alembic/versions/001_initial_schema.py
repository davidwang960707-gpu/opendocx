"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 用户表
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('admin', 'editor', 'viewer', name='userrole'), server_default='viewer'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    # 项目表
    op.create_table(
        'projects',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('brand_color', sa.String(7), server_default='#4F46E5'),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    # 版本表
    op.create_table(
        'versions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('is_default', sa.Boolean, server_default='false'),
        sa.Column('status', sa.Enum('draft', 'published', 'archived', name='versionstatus'), server_default='draft'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # 文档表
    op.create_table(
        'documents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('version_id', sa.String(36), sa.ForeignKey('versions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('parent_id', sa.String(36), sa.ForeignKey('documents.id'), nullable=True, index=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('slug', sa.String(200), nullable=False),
        sa.Column('content', sa.Text, nullable=True),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('status', sa.Enum('draft', 'published', 'archived', name='docstatus'), server_default='draft'),
        sa.Column('sort_order', sa.Integer, server_default='0'),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )
    # 版本+slug 联合唯一约束
    op.create_unique_constraint('uq_doc_version_slug', 'documents', ['version_id', 'slug'])

    # 构建日志表
    op.create_table(
        'build_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('version_id', sa.String(36), sa.ForeignKey('versions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('status', sa.Enum('pending', 'building', 'success', 'failed', name='buildstatus'), server_default='pending'),
        sa.Column('output', sa.Text, nullable=True),
        sa.Column('duration', sa.Integer, nullable=True),
        sa.Column('triggered_by', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('build_logs')
    op.drop_table('documents')
    op.drop_table('versions')
    op.drop_table('projects')
    op.drop_table('users')
    op.execute('DROP TYPE IF EXISTS buildstatus')
    op.execute('DROP TYPE IF EXISTS docstatus')
    op.execute('DROP TYPE IF EXISTS versionstatus')
    op.execute('DROP TYPE IF EXISTS userrole')
