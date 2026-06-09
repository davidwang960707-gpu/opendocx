#!/bin/bash
# OpenDocX 后端启动脚本（开发模式，--reload）
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY no_proxy NO_PROXY
cd "$(dirname "$0")/.."
# R12 配套: source ../.env (uvicorn 默认不读 .env)
if [ -f "../.env" ]; then
  set -a
  source "../.env"
  set +a
fi
exec venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload "$@"
