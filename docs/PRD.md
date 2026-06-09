# OpenDocX 产品需求文档（PRD）

## 1. 产品概述

### 1.1 产品定位

OpenDocX 是一个面向 AI / Vibe Coding 项目的文档管理、项目手册与静态站发布平台，帮助可运行的项目补齐可交付、可运营、可传播的最后一公里。

### 1.2 目标用户

| 角色 | 场景 |
|---|---|
| 技术 Writer | 编写和维护产品文档、API 文档 |
| 产品经理 | 管理文档版本、发布流程 |
| 开发者 | 搜索文档、查阅技术方案 |
| 运维 | 部署和维护文档平台 |

### 1.3 核心价值

1. **数据库驱动** — 文档存储在数据库，通过 Web 后台管理，无需 Git 操作
2. **AI 增强** — 语义搜索替代关键词匹配，降低文档检索成本
3. **私有化部署** — 全部数据存储在用户自己的服务器，无第三方依赖
4. **构建管线** — 数据库内容一键构建为可部署的静态站

---

## 2. 功能模块

### 2.1 用户认证（P0）

| 功能 | 状态 | 说明 |
|---|---|---|
| 邮箱密码登录 | ✅ 已完成 | JWT Token 认证 |
| 角色权限 | ✅ 已完成 | admin / editor / viewer 三级 |
| 密码加密 | ✅ 已完成 | PBKDF2-SHA256, 100000 次迭代 |
| Token 刷新 | ⬜ 待开发 | 无感续期 |

### 2.2 项目管理（P0）

| 功能 | 状态 | 说明 |
|---|---|---|
| 项目 CRUD | ✅ 已完成 | 创建、编辑、删除、列表 |
| 分页查询 | ✅ 已完成 | page / page_size 参数 |
| 品牌色配置 | ✅ 已完成 | 影响文档站主题色 |
| Logo 上传 | ⬜ 待开发 | 项目品牌标识 |

### 2.3 文档管理（P0）

| 功能 | 状态 | 说明 |
|---|---|---|
| 文档树 | ✅ 已完成 | 树形目录，支持父子关系 |
| Markdown 编辑器 | ✅ 已完成 | @uiw/react-md-editor 实时预览 |
| 版本管理 | ✅ 已完成 | 多版本并行（draft → published → archived） |
| 文档状态 | ✅ 已完成 | 草稿 / 已发布 / 已归档 |
| 拖拽排序 | ⬜ 待开发 | 调整文档顺序 |
| 图片上传 | ⬜ 待开发 | 编辑器内图片插入 |

### 2.4 AI 语义搜索（P1）

| 功能 | 状态 | 说明 |
|---|---|---|
| 向量搜索 | ✅ 已完成 | pgvector + cosine similarity |
| Embedding 生成 | ✅ 已完成 | sentence-transformers (BAAI/bge-m3) |
| 批量索引 | ✅ 已完成 | POST /api/v1/search/reindex |
| 降级方案 | ✅ 已完成 | 模型不可用时降级为 ILIKE |
| 前端搜索 UI | ⬜ 待开发 | 搜索框 + 结果展示 |
| 搜索结果高亮 | ⬜ 待开发 | 匹配片段高亮 |

### 2.5 构建与部署（P1）

| 功能 | 状态 | 说明 |
|---|---|---|
| 静态站构建 | ✅ 已完成 | 纯 Python HTML 生成，零 Node.js 依赖 |
| 构建日志 | ✅ 已完成 | 状态、耗时、输出记录 |
| 静态文件服务 | ✅ 已完成 | /docs/ 路径直接预览 |
| 文档站主题 | ✅ 已完成 | Apple 风格极简设计 |
| Docusaurus 构建 | ⬜ 待修复 | Node 23 兼容问题 |
| 增量构建 | ⬜ 待开发 | 仅重建变更文档 |

### 2.6 仪表盘（P2）

| 功能 | 状态 | 说明 |
|---|---|---|
| 统计概览 | ✅ 已完成 | 项目数、文档数、已发布数 |
| 项目卡片 | ✅ 已完成 | 品牌色圆点 + 描述 |
| 最近活动 | ⬜ 待开发 | 编辑 / 发布 / 构建时间线 |
| 文档阅读统计 | ⬜ 待开发 | 访问量、热门文档 |

---

## 3. 数据模型

### 3.1 ER 关系

```
User (1) ──→ (N) Project (created_by)
Project (1) ──→ (N) Version
Version (1) ──→ (N) Document
Document (1) ──→ (N) Document (parent_id, 自引用)
Document (1) ──→ (1) DocumentEmbedding
Version (1) ──→ (N) BuildLog
```

### 3.2 核心表

| 表 | 说明 | 关键字段 |
|---|---|---|
| users | 用户 | email, name, role, password_hash |
| projects | 项目 | name, slug, description, brand_color |
| versions | 版本 | project_id, version, is_default, status |
| documents | 文档 | version_id, title, slug, content, status, sort_order |
| document_embeddings | 向量索引 | document_id, embedding (vector 1024) |
| build_logs | 构建日志 | project_id, version_id, status, output, duration |

---

## 4. 非功能需求

| 需求 | 目标 | 当前状态 |
|---|---|---|
| API 响应时间 | < 200ms (P95) | ✅ 达标 |
| 并发支持 | 100 并发用户 | ⬜ 未测试 |
| 数据备份 | 每日自动备份 | ⬜ 待开发 |
| 文档大小 | 单文档 ≤ 100KB | ✅ 无限制 |
| 向量搜索延迟 | < 500ms | ✅ 达标 |
| 构建时间 | < 10s (50 篇文档) | ✅ 达标 |

---

## 5. 术语表

| 术语 | 说明 |
|---|---|
| pgvector | PostgreSQL 向量扩展，支持向量存储和相似度计算 |
| Embedding | 文本的向量表示，用于语义相似度计算 |
| cosine similarity | 余弦相似度，衡量两个向量的方向相似程度 |
| ILIKE | PostgreSQL 的不区分大小写模糊匹配 |
| RBAC | 基于角色的访问控制 |
| JWT | JSON Web Token，无状态认证机制 |
| SSE | Server-Sent Events, 后端单向推送流 (编辑器 AI 用) |
| Infima | Docusaurus 的 CSS 变量 token 体系, 本项目仿建 |
| Atlas EIDS | 9-color status palette + glassmorphism + dark purple sidebar design system |

---

## 6. Current Status (v0.1.0)

### 6.1 Current Capabilities

- **Core CRUD** ✅ Users, projects, documents, versions, RBAC, migrations, seeding
- **AI Integration** ✅ 6 editor actions with SSE streaming / semantic search via RAG / zero-LLM static analysis
- **Static Site Generation** ✅ mistune + Pygments + Infima + Atlas 9-color palette + glassmorphism + progress bar / dark mode / TOC / anchor links / responsive
- **Admin & Audit** ✅ User create/edit/disable/password reset + 49+ audit log entries + AdminRoute RBAC
- **Design System** ✅ Light sidebar (gray) / dark sidebar (purple) / floating pills / 6-tier breathing rhythm / 9-color status tags

### 6.2 Feature Maturity

| Area | Status | Notes |
|---|---|---|
| Backend API | Mature | FastAPI + SQLAlchemy 2.0, 10 test files, 45+ endpoints |
| Frontend UI | Mature | React 18 + Ant Design 5, 11 pages, Zustand state |
| AI Capabilities | Functional | LLM streaming + embedding search, 6 editor actions |
| Build Pipeline | Functional | 1820-line `build_service.py`, mistune + Pygments + Mermaid |
| Test Coverage | Solid | 10 backend test files, 71+ tests |
| Deployment | Ready | Docker Compose + Nginx, full CI/CD |
| Design System | Strong | Atlas EIDS 9-color palette + 6-tier breathing rhythm |
| Documentation | Strong | USER-GUIDE + API + ARCHITECTURE + PRD + ROADMAP |

### 6.3 Roadmap Highlights

See [ROADMAP.md](ROADMAP.md) for full details. Key upcoming features:

- **AI in the published static site** (chat widget, per-page explain) - v0.2.0
- **MDX support** (Markdown + JSX, like Docusaurus) - v0.3.0
- **Real-time collaboration** (multi-user editing with OT/CRDT) - v0.3.0
- **Workflow improvements** (review, approval, comments, track changes) - v0.3.0
- **Better search** (BM25 + vector hybrid) - v0.2.0
- **Live demo URL** (public, free) - v0.2.0

### 6.4 Known Limitations (v0.1.0)

- **No real-time collaboration**: Multiple users editing the same document may overwrite each other
- **No MDX support**: Only standard Markdown (no JSX in docs)
- **Basic search**: Vector search only, no keyword-based fallback
- **Single-language static site**: One project per language (multi-language static sites planned)
- **No refresh tokens**: Re-login required after 7 days
- **No webhook integrations**: External systems can't subscribe to document changes

These are tracked in [ROADMAP.md](ROADMAP.md) and will be addressed in v0.2.0 / v0.3.0.
