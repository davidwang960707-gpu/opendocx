# Contributing to OpenDocX

First off, thank you for considering contributing to OpenDocX!
We welcome bug reports, feature requests, documentation improvements, and pull requests.

> 注:本仓库社区文档**禁止在 UI 文本中用 emoji**(项目协作规则 #5)。上面  仅出现在 markdown 文档装饰里,不影响产品代码。

## Code of Conduct

This project and everyone participating in it is governed by the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Project Structure

```
opendocx/
├── backend/                # FastAPI Python 后端
│   ├── app/
│   │   ├── main.py        # FastAPI 入口
│   │   ├── routers/       # REST/SSE 端点
│   │   ├── services/      # 业务逻辑 (build_service, llm, editor_ai)
│   │   ├── schemas/       # Pydantic 模型 (6 域)
│   │   ├── models/        # SQLAlchemy ORM
│   │   └── db/            # PostgreSQL session
│   ├── tests/             # 10 个 pytest 文件
│   ├── scripts/           # start-backend.sh
│   └── venv/              # Python 3.9.6 venv
├── frontend/              # React 18 + TypeScript + Vite
│   ├── src/
│   │   ├── pages/         # 11 个页面 (Login/Projects/Documents/Published/...)
│   │   ├── components/    # Editor/AIFloatingActions/PreBuildModal/...
│   │   ├── services/      # api.ts editorApi.ts
│   │   ├── types/         # TypeScript 类型
│   │   └── styles/        # CSS / tokens.css
│   └── vite.config.ts     # 3077 端口, /api proxy → 8001
├── docs/                  # 58 张截图 + 收工总结 + 对标报告
├── data/                  # 运行时数据 (DB / 构建产物)
└── .env.example           # LLM key + DB 模板
```

## Development Setup

### Prerequisites

- Python 3.9.6+ (3.12 也支持)
- Node.js 18+
- PostgreSQL 14+ with `pgvector` extension
- Redis 6+ (用于 rate limit)

### 1. 克隆 + 启动 DB

```bash
git clone https://github.com/<your-org>/opendocx.git
cd opendocx

# 启动 PostgreSQL (Mac 用 brew, 详见 docker-compose.yml)
createdb opendocx_dev
psql opendocx_dev -c "CREATE EXTENSION pgvector;"

# 启动 Redis
redis-server --daemonize yes
```

### 2. 后端

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 复制 env 模板
cp ../.env.example ../.env
# 编辑 .env: 填 LLM_API_KEY / DATABASE_URL / REDIS_URL

bash scripts/start-backend.sh    # R12 配套,auto-source .env
# 后端跑在 http://127.0.0.1:8001
```

### 3. 前端

```bash
cd frontend
npm install
npx vite --host 127.0.0.1 --port 3077
# 前端跑在 http://127.0.0.1:3077
```

### 4. 登录

默认 admin: `admin@opendocx.local` / `admin123` (首次启动 seed)

## Pull Request Process

### 1. Fork + Branch

```bash
git checkout -b feature/<short-name>   # 例: feature/r16-static-ai-tip
# 或
git checkout -b fix/<bug-id>           # 例: fix/race-condition-publish
```

### 2. Commit 格式 (项目协作规则 v3 #3: 修+验证 一次 commit 收)

我们用 Conventional Commits:

```
<type>(<scope>): <description> (估时)

类型: feat | fix | docs | refactor | test | chore | perf
scope: opendocx (主项目) | <sub-module> | decision
description: 中文一句话, 含真根因 (不仅是"fix bug")
估时: (0.1d ~ 5d)

例:
  fix(opendocx): R11 - QA 选区没送进 LLM (0.2d)
  feat(opendocx): R15 预构建弹窗 - doc 树 + 单/批量发布 (0.8d)
  docs(decision): OpenDocX vs Docusaurus 对标报告 (0.2d)
```

### 3. PR Description 必含

PR 描述里**必填真根因 + 验证证据** (项目协作规则 v3 #6 "啥也不是" 反例):
- **根因** — 不只是"修了个 bug",而是要 1 句话说清
- **改动** — 文件级别 (+行 / -行)
- **验证** — TestClient 单测结果 / 浏览器 E2E 截图 / DB 真实状态变化
- **风险** — 列出 0-2 个潜在副作用

### 4. 验证标准 (项目协作规则 v3 #6)

- [ ] 后端改动:对应 test_*.py 通过(`cd backend && source venv/bin/activate && pytest tests/test_<x>.py -v`)
- [ ] 前端改动:`npx tsc --noEmit` 0 错
- [ ] 浏览器 E2E:截图 + 关键操作流程
- [ ] 0 mock 数据:真实 API + 真实 DB 验证
- [ ] 0 emoji:UI 文本无 unicode emoji(用 SVG / 中文 / 文字)
- [ ] 0 新依赖(必需时,先开 issue 讨论)

### 5. PR 通过条件

- [ ] 1 个或以上 maintainer review 通过
- [ ] CI (GitHub Actions) 全绿
- [ ] 没遗留"修+没测"或"测+没修"的拆 commit
- [ ] 文档同步更新(如果改了用户可见行为)

## Issue Reporting

### Bug Report 模板 (`.github/ISSUE_TEMPLATE/bug_report.md`)

- 复现步骤
- 期望行为 vs 实际行为
- 环境 (OS / Python / Node / DB 版本)
- 后端日志 (R12 起的 503 错误含中文说明)
- 截图或 GIF

### Feature Request 模板 (`.github/ISSUE_TEMPLATE/feature_request.md`)

- 痛点描述
- 项目协作规则 #4: 提交前先**列方案 3 选 1**(根因 / 3 路径 / 工作量估算)
- 优先级 (P0-P3)
- 验收标准

## Commit Author 署名

第一次提交前请确保 git config 设好:
```bash
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

我们鼓励在 commit message 里加 `Co-authored-by:` 标注共同作者 (项目协作规则 #0: 协作透明)。

## 联系方式

- GitHub Issues: 主沟通渠道
- Discussions: 架构 / 路线 / RFC
- Security: 见 [SECURITY.md](SECURITY.md) (别在 issue 里贴漏洞细节)

## License

贡献的代码默认采用 [Apache License 2.0](LICENSE),与项目一致。
