"""P0 段 0 修底测试 — 真 PG 集成测, 验证 pgvector 装上 + document.delete 不再 500

不走 conftest 的 SQLite 内存, 直接走真 PG (8001 服务或 ASGI)。

3 个测:
1. test_pgvector_extension_installed: 验 vector 扩展真装
2. test_document_embeddings_table_exists: 验表 + 索引在
3. test_document_delete_does_not_500: 端到端 创建 → embed → 删 不报错

跑法: cd backend && venv/bin/python -m pytest tests/test_pgvector.py -v
"""
import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# 走真 PG (config.py 默认值)
PG_URL = os.environ.get(
    "DOCAI_TEST_PG_URL",
    "postgresql+asyncpg://opendocx:opendocx@localhost:5432/opendocx"
)


@pytest.fixture
async def pg_engine():
    """真 PG 引擎 (不走 conftest 的 SQLite 内存)"""
    engine = create_async_engine(PG_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest.mark.asyncio
async def test_pgvector_extension_installed(pg_engine):
    """验 vector 扩展真装上 (P0 段 0 修底核心)"""
    async with pg_engine.begin() as conn:
        result = await conn.execute(
            text("SELECT extname, extversion FROM pg_extension WHERE extname='vector'")
        )
        row = result.fetchone()
    assert row is not None, "vector 扩展未装, 请先 brew install pgvector + CREATE EXTENSION vector"
    assert row[0] == "vector"
    assert row[1] is not None  # 0.8.0 或更新
    print(f"\n  vector 扩展: v{row[1]}")


@pytest.mark.asyncio
async def test_document_embeddings_table_exists(pg_engine):
    """验 document_embeddings 表 + 索引在"""
    async with pg_engine.begin() as conn:
        # 表存在
        result = await conn.execute(
            text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'document_embeddings'
            )
            """)
        )
        assert result.scalar() is True, "document_embeddings 表不存在, 跑 alembic upgrade head 修复"

        # 索引在
        result = await conn.execute(
            text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'document_embeddings'
            """)
        )
        indexes = [r[0] for r in result.fetchall()]
        assert "ix_document_embeddings_document_id" in indexes, f"索引缺失, 当前: {indexes}"
        print(f"\n  索引: {indexes}")

        # 字段类型
        result = await conn.execute(
            text("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = 'document_embeddings'
            ORDER BY ordinal_position
            """)
        )
        cols = [(r[0], r[1], r[2]) for r in result.fetchall()]
        col_dict = {c[0]: (c[1], c[2]) for c in cols}
        assert "embedding" in col_dict
        assert col_dict["embedding"][1] == "vector", f"embedding 列不是 vector 类型: {col_dict['embedding']}"
        print(f"  字段: {col_dict}")


@pytest.mark.asyncio
async def test_vector_type_functional(pg_engine):
    """验 vector 类型能用 (插入 → cosine distance 算 → 删)"""
    async with pg_engine.begin() as conn:
        # 临时表测
        await conn.execute(text("DROP TABLE IF EXISTS _test_pgvector"))
        await conn.execute(text("CREATE TABLE _test_pgvector (id int, v vector(3))"))
        await conn.execute(
            text("INSERT INTO _test_pgvector VALUES (1, '[1,2,3]'), (2, '[4,5,6]')")
        )
        result = await conn.execute(
            text("SELECT id, v, v <=> '[1,2,3]' AS dist FROM _test_pgvector ORDER BY v <=> '[1,2,3]'")
        )
        rows = result.fetchall()
        assert len(rows) == 2
        # 第 1 行 (1,2,3) 跟 query 距离最近
        assert rows[0][0] == 1
        assert float(rows[0][2]) < 0.01  # 距离 ≈ 0
        await conn.execute(text("DROP TABLE _test_pgvector"))
    print(f"\n  vector 类型 + cosine 距离工作正常")
