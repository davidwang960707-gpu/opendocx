"""add document_embeddings table

Revision ID: 002
Revises: 001
Create Date: 2026-06-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 确保 pgvector 扩展存在
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 创建文档嵌入表
    op.create_table(
        'document_embeddings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('document_id', sa.String(36), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('embedding', Vector(1024), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('ix_document_embeddings_document_id', 'document_embeddings', ['document_id'])


def downgrade() -> None:
    op.drop_index('ix_document_embeddings_document_id', table_name='document_embeddings')
    op.drop_table('document_embeddings')
