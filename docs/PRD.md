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
| 拖拽排序 | ✅ 已完成 | 文档树支持拖拽重排和父子层级调整 |
| 图片上传 | ✅ 已完成 | 版本资产库支持图片、GIF、视频和常见附件上传，编辑器可插入 Markdown 引用 |

### 2.4 AI 语义搜索（P1）

| 功能 | 状态 | 说明 |
|---|---|---|
| 向量搜索 | ✅ 已完成 | pgvector + cosine similarity |
| Embedding 生成 | ✅ 已完成 | sentence-transformers (BAAI/bge-m3) |
| 批量索引 | ✅ 已完成 | POST /api/v1/search/reindex |
| 降级方案 | ✅ 已完成 | 模型不可用时降级为 ILIKE |
| 前端搜索 UI | ⬜ 待开发 | 搜索框 + 结果展示 |
| 搜索结果高亮 | ⬜ 待开发 | 匹配片段高亮 |

### 2.4.1 编辑器 AI 与文档分析（P1）

| 功能 | 状态 | 说明 |
|---|---|---|
| 编辑器 AI 浮层 | ✅ 已完成 | 选中文本后触发，走 `/api/v1/editor/ai` SSE 流式接口 |
| LLM Provider 配置 | ✅ 已完成 | 兼容 OpenAI 风格 Chat Completions，可配置 provider/base_url/model/key |
| 续写 / 改写 / 解释 / 问答 / 总结 / 润色 | ✅ 已完成 | 6 个动作均由后端集中组装 prompt 并调用真实 LLM provider |
| 人工确认应用 | ✅ 已完成 | AI 输出进入对比弹窗，用户确认后才替换或追加到文档 |
| 文档 Insight | ✅ 已完成 | 规则分析术语、接口、摘要、健康度和相关文档，不冒充 LLM 输出 |
| 生成 OpenAPI / SDK / 测试 | ⬜ 后续规划 | v0.1.0-alpha 不提供假入口，后续版本需接入真实 prompt 与上下文 |

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
| Atlas EIDS | 9 色状态体系、轻玻璃质感和后台布局 token |

---

## 6. 当前状态（v0.1.0-alpha）

### 6.1 已具备能力

- **核心增删改查** ✅ 用户、项目、文档、版本、权限、迁移和 Demo seed。
- **AI 集成** ✅ 6 类编辑动作、SSE 流式返回、语义搜索和规则化文档分析。
- **静态站构建** ✅ mistune、Pygments、主题 token、阅读进度、深浅主题、目录和锚点。
- **管理与审计** ✅ 用户创建、编辑、禁用、密码重置、审计日志和管理员路由保护。
- **设计体系** ✅ 浅色侧栏、项目主题色、状态标签、表格密度和轻动效基础。

### 6.2 成熟度

| 模块 | 状态 | 说明 |
|---|---|---|
| 后端 API | 较成熟 | FastAPI + SQLAlchemy 2，核心接口已覆盖 |
| 前端 UI | 可用 | React + Ant Design，后台主链路已完成 |
| AI 能力 | 可用 | LLM 流式返回、向量检索、编辑器动作；右侧 Insight 为规则分析 |
| 构建链路 | 可用 | `build_service.py` 负责 Markdown 到静态站 |
| 测试覆盖 | 需增强 | 后端已有测试，前端测试仍需补齐 |
| 部署 | 可试用 | Docker Compose 与 Nginx 配置已提供 |
| 文档 | 可开源 | 中文 README、用户指南、架构、API、路线图已准备 |

### 6.3 路线图摘要

完整计划见 [ROADMAP.md](ROADMAP.md)。关键方向：

- **静态站 AI 能力**：读者侧问答、页面解释和反馈增强。
- **媒体资产管理**：资产库搜索、筛选、重命名、批量删除和粘贴上传。
- **更强搜索**：关键词与向量混合检索。
- **协作流程**：评审、审批、评论和变更记录。
- **公开演示站**：降低首次试用成本。

### 6.4 已知限制

- 暂无实时协同，多人编辑同一文档时可能覆盖。
- 暂不支持 MDX，只支持标准 Markdown 与扩展语法。
- 搜索能力仍偏基础。
- 静态站多语言建议先用不同项目或版本管理。
- 暂无 refresh token，token 过期后需要重新登录。
- 暂无 webhook 集成。

这些限制会在 v0.2.0 和 v0.3.0 继续处理。
