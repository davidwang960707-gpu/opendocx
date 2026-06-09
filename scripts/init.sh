#!/bin/bash
# OpenDocX 初始化脚本
set -e

echo "=== OpenDocX 初始化 ==="

# 1. 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "错误: 请先安装 Docker"
    exit 1
fi

# 2. 复制环境变量
if [ ! -f .env ]; then
    cp .env.example .env
    echo "已创建 .env 文件，请编辑配置后重新运行"
    exit 0
fi

# 3. 启动基础设施
echo "启动服务..."
docker compose up -d postgres redis

# 等待 PostgreSQL 就绪
echo "等待 PostgreSQL 就绪..."
sleep 5
until docker compose exec postgres pg_isready -U opendocx; do
    sleep 2
done

# 4. 启动后端
echo "启动后端..."
docker compose up -d backend
sleep 3

# 5. 运行种子数据
echo "创建种子数据..."
docker compose exec backend python scripts/seed.py

# 6. 启动前端和 Nginx
echo "启动前端..."
docker compose up -d frontend nginx

echo ""
echo "=== OpenDocX 初始化完成 ==="
echo ""
echo "管理后台: http://localhost"
echo "文档站:   http://localhost/docs"
echo "API:      http://localhost:8000"
echo ""
echo "登录账号: admin@opendocx.local / admin123"
