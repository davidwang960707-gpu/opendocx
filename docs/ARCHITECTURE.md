# OpenDocX 架构说明

本文面向希望理解、二次开发或贡献 OpenDocX 的开发者。

## 1. 总览

OpenDocX 是一个三层应用：

```text
浏览器
  ↓
React 管理后台
  ↓
FastAPI 后端
  ↓
PostgreSQL / pgvector
```

核心链路是：

```text
项目 → 版本 → 文档树 → Markdown 内容 → 发布确认 → 静态站构建 → 读者反馈 → 后台审核
```

## 2. 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | React 18、TypeScript、Ant Design 5、Vite、Zustand |
| 后端 | FastAPI、SQLAlchemy 2、Alembic、Pydantic |
| 数据库 | PostgreSQL、pgvector |
| AI | 可配置 LLM Provider，兼容 OpenAI 风格接口 |
| Markdown | mistune、Pygments、自定义渲染样式 |
| 部署 | Docker Compose、Nginx |

## 3. 后端结构

```text
backend/
  app/
    main.py              # FastAPI 入口
    config.py            # 配置
    database.py          # 数据库连接
    models/              # SQLAlchemy 模型
    schemas/             # Pydantic 模型
    routers/             # API 路由
    services/            # 业务服务
    scripts/             # seed 与维护脚本
  alembic/               # 数据库迁移
  tests/                 # 后端测试
```

主要路由：

| 路由 | 说明 |
| --- | --- |
| `/api/v1/auth/*` | 登录、当前用户、修改密码 |
| `/api/v1/projects/*` | 项目、版本 |
| `/api/v1/documents/*` | 文档树、文档内容、导入 |
| `/api/v1/build/*` | 构建、发布站点 |
| `/api/v1/editor/*` | AI 编辑辅助 |
| `/api/v1/feedback/*` | 静态站反馈 |
| `/api/v1/users/*` | 用户管理 |
| `/api/v1/audit-logs` | 审计日志 |

## 4. 数据模型

```text
User
  └── Project
        └── Version
              └── Document
                    └── DocumentEmbedding

Feedback
AuditLog
```

关键关系：

- 一个用户可以创建多个项目。
- 一个项目可以有多个版本。
- 一个版本下有一棵文档树。
- 文档通过 `parent_id` 形成文件夹和文档层级。
- 已发布文档会进入静态站构建。
- 操作会写入审计日志。

## 5. 认证与权限

v0.1.0-alpha 使用 JWT 认证。

流程：

1. 前端提交邮箱和密码。
2. 后端校验密码哈希。
3. 后端生成 JWT。
4. 前端把 token 存入 `localStorage`。
5. 后续请求通过 `Authorization: Bearer <token>` 访问。

角色：

| 角色 | 权限 |
| --- | --- |
| admin | 管理项目、文档、构建、用户、审计 |
| editor | 管理自己的项目和文档 |
| viewer | 预留角色，面向只读场景 |

## 6. AI 服务

AI 能力分为两类：

- 编辑器 AI 浮层：通过 `services/llm/` 调用 OpenAI 风格 Chat Completions 接口，SSE 流式返回。
- 文档 Insight：通过 `services/ai_analyzer.py` 做规则分析，不调用 LLM，不冒充生成式 AI 输出。

LLM Provider 默认兼容 OpenAI 风格接口。

常见配置：

```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-key
LLM_MODEL=gpt-4o-mini
```

编辑器 AI 输出通过 SSE 流式返回，前端逐步渲染。文档 Insight 直接返回结构化 JSON。

## 7. 静态站构建

静态站构建是 OpenDocX 的核心能力之一。

构建流程：

1. 读取项目、版本和已发布文档。
2. 构造文档树。
3. 用 mistune 解析 Markdown。
4. 用 Pygments 渲染代码高亮。
5. 注入提示块、表格、图片、视频、公式、Mermaid 等样式。
6. 生成 HTML 页面、静态 CSS 和脚本。
7. 写入 `data/builds/<project>/<version>/`。

产物是纯静态文件，不依赖 React 运行时。

## 8. 前端结构

```text
frontend/
  src/
    pages/          # 页面
    components/     # 通用组件
    layouts/        # 主布局
    services/       # API 客户端
    stores/         # Zustand 状态
    styles/         # 全局样式
    types/          # TypeScript 类型
```

主要页面：

| 路径 | 页面 |
| --- | --- |
| `/login` | 登录 |
| `/` | 首页 |
| `/projects` | 项目列表 |
| `/projects/:id` | 项目详情 |
| `/projects/:id/docs` | 文档编辑 |
| `/published` | 已发布站点 |
| `/feedbacks` | 反馈审核 |
| `/settings` | 设置 |
| `/admin/users` | 用户管理 |
| `/admin/audit` | 审计日志 |

## 9. 设计原则

- 后台以中文操作效率为优先。
- 浅色主题保持干净统一，项目主题色用于强调而不是铺满页面。
- 表格和列表优先保证可读性、动态列宽和筛选能力。
- 静态站阅读体验可以强于后台编辑预览。
- 所有关键操作都应该有状态反馈，而不只依赖 toast。

## 10. 安全边界

当前版本已覆盖：

- 密码哈希存储。
- JWT 认证。
- 管理员路由保护。
- Markdown 默认转义与清洗。
- 反馈限流和垃圾反馈基础判断。
- 审计日志。

仍需增强：

- Refresh token。
- 更细粒度项目权限。
- 媒体上传安全扫描。
- 静态站 CSP。
- 生产级日志和告警。

## 11. 本地开发命令

后端：

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

前端：

```bash
cd frontend
npm ci
npx vite --host 0.0.0.0 --port 3077
```

Demo 数据：

```bash
bash scripts/seed_demo.sh
```

## 12. 贡献建议

提交 PR 前请确认：

- 真实 API 和真实数据库跑通。
- 关键界面有截图或说明。
- 修改涉及的文档同步更新。
- 不提交 `.env`、本地数据、构建产物和个人路径。
