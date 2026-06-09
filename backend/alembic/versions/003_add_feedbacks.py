"""add document_feedbacks table (reader like/dislike/bookmark/comment)

Revision ID: 003
Revises: 002
Create Date: 2026-06-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'document_feedbacks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('document_id', sa.String(36),
                  sa.ForeignKey('documents.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('version_id', sa.String(36),
                  sa.ForeignKey('versions.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('kind',
                  sa.Enum('like', 'dislike', 'bookmark', 'comment',
                          name='feedback_kind'),
                  nullable=False, index=True),
        sa.Column('visitor_id', sa.String(64), nullable=False, index=True),
        sa.Column('user_id', sa.String(36),
                  sa.ForeignKey('users.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('user_name', sa.String(100), nullable=True),
        sa.Column('body', sa.Text, nullable=True),
        sa.Column('parent_id', sa.String(36),
                  sa.ForeignKey('document_feedbacks.id', ondelete='CASCADE'),
                  nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(),
                  onupdate=sa.func.now()),
    )
    # 复合索引: (document_id, kind) 用于快速统计
    op.create_index(
        'ix_feedbacks_doc_kind', 'document_feedbacks',
        ['document_id', 'kind'],
    )
    # 复合索引: (document_id, visitor_id) 用于查找某人对此 doc 的反应
    op.create_index(
        'ix_feedbacks_doc_visitor', 'document_feedbacks',
        ['document_id', 'visitor_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_feedbacks_doc_visitor', table_name='document_feedbacks')
    op.drop_index('ix_feedbacks_doc_kind', table_name='document_feedbacks')
    op.drop_table('document_feedbacks')
    op.execute("DROP TYPE IF EXISTS feedback_kind")
