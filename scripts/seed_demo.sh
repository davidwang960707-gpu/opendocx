#!/usr/bin/env bash
# scripts/seed_demo.sh - seed demo data for a first local run
#
# Usage:
#   bash scripts/seed_demo.sh
#
# Prerequisite:
#   - PostgreSQL 已启动 + DATABASE_URL 配置正确
#   - 后端 venv 已创建 (cd backend && python -m venv venv)
#   - alembic 迁移已跑 (cd backend && alembic upgrade head)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "=========================================="
echo "OpenDocX Demo Data Seeder"
echo "=========================================="
echo ""
echo "Project root: $PROJECT_ROOT"
echo ""

# 1. 检查后端 venv
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo "ERROR: backend/venv not found."
    echo "Please run: cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# 2. 检查 .env
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "ERROR: .env not found."
    echo "Please run: cp .env.example .env && edit .env to fill in LLM_API_KEY etc."
    exit 1
fi

# 3. 检查 PostgreSQL 可达
echo "[1/4] Checking PostgreSQL connection..."
cd "$BACKEND_DIR"
source venv/bin/activate
if ! env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u SOCKS_PROXY -u socks_proxy python -c "
import asyncio
from app.database import engine
from sqlalchemy import text
async def check():
    async with engine.begin() as conn:
        await conn.execute(text('SELECT 1'))
    await engine.dispose()
asyncio.run(check())
print('  ok PostgreSQL reachable')
" 2>&1; then
    echo "ERROR: Cannot connect to PostgreSQL. Check DATABASE_URL in .env"
    exit 1
fi

# 4. 跑 alembic 迁移
echo ""
echo "[2/4] Running alembic migrations..."
if ! env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u SOCKS_PROXY -u socks_proxy alembic upgrade head 2>&1; then
    echo "ERROR: alembic upgrade failed"
    exit 1
fi

# 5. Seed demo
echo ""
echo "[3/4] Seeding demo data..."
if ! env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u SOCKS_PROXY -u socks_proxy python -m app.scripts.seed_demo 2>&1; then
    echo "ERROR: seed_demo failed"
    exit 1
fi

# 6. 完成
echo ""
echo "[4/4] Done!"
echo ""
echo "=========================================="
echo "Demo data ready!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Start backend:  bash backend/scripts/start-backend.sh"
echo "  2. Start frontend: cd frontend && npx vite --port 3077"
echo "  3. Open:           http://localhost:3077"
echo "  4. Login:          admin@opendocx.local / admin123"
echo ""
echo "Want to clean up demo data later?"
echo "  psql: DELETE FROM projects WHERE slug = 'welcome-to-opendocx';"
echo ""
