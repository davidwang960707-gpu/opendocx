#!/bin/bash
# OpenDocX 后端启动脚本（清代理版本，适配 SOCKS 代理污染的终端环境）
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY no_proxy NO_PROXY
cd "$(dirname "$0")/.."
# R12 配套: source ../.env 让 LLM_API_KEY 等生效 (uvicorn 默认不读 .env)
# set -a 让所有已定义变量自动 export, set +a 关闭
if [ -f "../.env" ]; then
  set -a
  source "../.env"
  set +a
fi
exec venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 "$@"
