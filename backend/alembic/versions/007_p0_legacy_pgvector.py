"""007 (P0-legacy) 补建 document_embeddings 表 — 1.0 漏了 002

Revision ID: 007
Revises: 006
Create Date: 2026-06-06

1.0 阶段: 002_add_embeddings.py migration 写好了, 但因为 pgvector 扩展没装, 002
从来没真跑过 (alembic 跳过非空 transaction)。后续 003-006 migration 假设 document_embeddings
表存在, 但实际上没建。

2026-06-06 P0 段 0 修底: 装 pgvector 0.8.0 (brew) → 手动建表 → 写 007 migration
记录这次"补建", 避免未来 alembic 看到 002 + 007 状态不对再删表。

本 migration 走 IF NOT EXISTS 模式, 幂等: 表已存在则 skip。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) 装 vector 扩展 (幂等, 已装则 NOTICE 跳过)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2) 创 document_embeddings 表 (幂等, IF NOT EXISTS)
    op.execute("""
        CREATE TABLE IF NOT EXISTS document_embeddings (
            id VARCHAR(36) PRIMARY KEY,
            document_id VARCHAR(36) NOT NULL UNIQUE REFERENCES documents(id) ON DELETE CASCADE,
            embedding vector(1024) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # 3) 创索引 — 1.0 手动建过, 可能 owner 不对; 改用 DO block 检查存在性
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'document_embeddings'
                AND indexname = 'ix_document_embeddings_document_id'
            ) THEN
                CREATE INDEX ix_document_embeddings_document_id
                ON document_embeddings (document_id);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # 注意: 不 drop 扩展 (可能别的库也用), 只 drop 表
    op.execute("DROP INDEX IF EXISTS ix_document_embeddings_document_id")
    op.execute("DROP TABLE IF EXISTS document_embeddings")
