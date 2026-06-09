"""测试通用 fixtures"""
import os
# 测试环境禁用 rate limit（避免多 test 共享 client IP 触发 429）
os.environ.setdefault("DISABLE_RATE_LIMIT", "1")

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.models import Base
from app.database import get_db
from app.main import app

# 使用 SQLite 内存数据库做测试（不依赖 PostgreSQL）
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 不 drop：让 session 期间数据可被后续 test 看到（避免重复 seed）
    # session 结束后由 fixture teardown 清理


async def override_get_db():
    async with TestSession() as session:
        try:
            yield session
        finally:
            await session.close()

app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def admin_token(client: AsyncClient):
    """创建管理员并返回 token（需要先 seed 数据库）"""
    # 注：测试环境需要先插入管理员用户
    # 这里直接登录已知的测试用户
    from app.utils.auth import hash_password
    from sqlalchemy.exc import IntegrityError
    async with TestSession() as session:
        from app.models import User, UserRole
        admin = User(
            email="test@opendocx.local",
            name="Test Admin",
            password_hash=hash_password("test123"),
            role=UserRole.admin,
        )
        session.add(admin)
        try:
            await session.commit()
        except IntegrityError:
            # 邮箱已存在（多 test 共享 setup_db 时）— 直接用现有用户
            await session.rollback()

    resp = await client.post("/api/v1/auth/login", json={"email": "test@opendocx.local", "password": "test123"})
    if "data" not in resp.json():
        raise RuntimeError(f"login failed: {resp.status_code} {resp.text}")
    return resp.json()["data"]["access_token"]
