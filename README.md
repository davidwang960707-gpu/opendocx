# OpenDocX

<div align="center">

  <img src="https://github.com/davidwang960707-gpu.png" width="120" height="120" alt="王六 avatar" />

  <h3>OpenDocX · AI / Vibe Coding 文档管理与静态站发布平台</h3>

  <h3>打通VibeCoding最后一公里</h3>

  <p>
    把 AI 生成项目的 README、使用手册、交付说明、发布站点和反馈闭环，收拢进一个可编辑、可审核、可发布的开源工作台。
  </p>


  <p>
    <img src="https://img.shields.io/badge/AI%20Docs-Management%20Platform-111827?style=for-the-badge&logo=openai&logoColor=white" alt="AI Docs Management Platform" />
    <img src="https://img.shields.io/badge/Vibe%20Coding-Delivery%20Ready-7B61FF?style=for-the-badge&logo=gitbook&logoColor=white" alt="Vibe Coding Delivery Ready" />
    <img src="https://img.shields.io/badge/Static%20Site-Publishing-0EA5E9?style=for-the-badge&logo=githubpages&logoColor=white" alt="Static Site Publishing" />
  </p>
  <p>
    <a href="https://davidwang960707-gpu.github.io/opendocx/showcase/render-showcase.html">在线预览：OpenDocX 静态站渲染能力速查</a>
  </p>
  <p>
    <img src="https://img.shields.io/badge/React%2018-TypeScript-4F46E5?style=for-the-badge&logo=react&logoColor=white" alt="React TypeScript" />
    <img src="https://img.shields.io/badge/FastAPI-Python%203.12-22C55E?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI Python" />
    <img src="https://img.shields.io/badge/PostgreSQL-pgvector-2563EB?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL pgvector" />
  </p>
</div>

---

## 这是什么

OpenDocX 解决的是一个很现实的尾部问题：AI 已经能很快生成可运行项目，但项目文档、使用手册、交付说明、发布站点和反馈闭环往往仍然散落在聊天记录、临时 Markdown、README 片段和个人笔记里。OpenDocX 把这些内容集中到一个可编辑、可审核、可发布的工作台里，让项目更容易被交付、传播和长期维护。

## 界面预览

![OpenDocX 后台概览](docs/screenshots/01-dashboard.png)

后台提供项目、文档、发布、反馈和审计的统一工作台，适合把 AI 生成项目从“能跑”推进到“能交付、能发布、能维护”。

项目可以维护独立主题色、版本、状态和文档树，适合同时管理多个 Vibe Coding 项目的文档资产。

![OpenDocX 编辑器与 AI 浮层](docs/screenshots/03-editor-ai.png)

编辑器内选中文本即可唤起 AI 浮层，也可以通过右侧 AI Insight 查看术语一致性、摘要、健康度和推荐动作。

![OpenDocX 命令面板](docs/screenshots/04-command-palette.png)

命令面板把导航、文档操作、构建发布和 AI 动作集中到一个入口，减少在复杂后台里的来回跳转。

![OpenDocX 预构建确认](docs/screenshots/05-build-modal.png)

构建前会确认本次发布包含哪些文档、哪些已发布、哪些仍未发布，避免把草稿误带到静态站。

![OpenDocX 静态站浅色渲染](docs/screenshots/06-static-site-light.png)

![OpenDocX 静态站深色渲染](docs/screenshots/07-static-site-dark.png)

静态站面向读者体验优化，支持浅色/深色主题、右侧目录、提示块、代码高亮、表格、图片、视频和反馈讨论。

![OpenDocX 读者反馈与讨论](docs/screenshots/08-feedback-comments.png)

## 适合谁用

- 用 AI / Vibe Coding 快速做出项目，但还缺少完整文档和交付手册的开发者。
- 需要维护产品手册、API 文档、实施文档、FAQ 的小团队。
- 希望用 Web 后台管理文档树、版本、发布、反馈和审计记录的开源项目。
- 想把数据库里的文档一键构建成可独立部署静态站的团队。

## 核心能力

### 1. 项目与版本管理

- 每个项目可以维护独立主题色、描述、版本和文档树。
- 支持项目列表、项目详情、版本视图和发布状态管理。
- Demo 数据使用公开示例，不包含内部项目数据。

### 2. 文档树与 Markdown 编辑

- 支持文件夹、子文件夹、文档排序和发布状态。
- 三栏编辑体验：文档树、Markdown 编辑区、预览/AI 辅助区。
- 后台编辑器强调效率；静态站渲染强调阅读体验，两者职责分离。

### 3. AI 辅助写作

编辑器 AI 浮层是 OpenDocX 面向 AI / Vibe Coding 文档交付场景的关键体验：用户在 Markdown 编辑器里选中一段文字后，可以直接在原位唤起 AI 操作，不需要把上下文复制到聊天窗口再粘回来。

- 支持选中文本后触发 AI 浮层，围绕当前段落做续写、改写、摘要、翻译、解释和问答。
- 保留人工确认链路，AI 生成内容不会直接覆盖原文，适合把粗糙草稿打磨成项目手册、交付说明、FAQ 和发布文档。
- 浮层与编辑区同屏工作，适合局部润色、术语统一、长段落压缩和面向读者的解释补充。
- 支持命令面板快速触发保存、发布、构建、上传 Markdown、跳转项目和 AI 总结等高频动作。
- LLM Provider 可配置，兼容 OpenAI 风格接口，团队可以接入自己的模型网关或私有化大模型服务。

### 4. 发布前确认与静态站构建

- 构建前先展示发布确认，避免草稿未发布就生成站点。
- 支持把数据库文档构建为纯静态 HTML/CSS/JS。
- 静态站支持浅色/深色主题、目录、阅读进度、搜索入口、反馈入口。
- Markdown 渲染支持表格、任务列表、提示块、代码高亮、图片、视频链接、iframe 容器、Mermaid 占位与公式占位级样式。

### 5. 反馈审核、用户管理和审计

- 访客可在静态站提交反馈。
- 后台可审核反馈、查看来源文档和处理状态。
- 管理员可维护用户、角色、启停状态和密码重置。
- 审计日志记录关键操作，便于排查和合规留痕。

## 快速开始

### 方式一：Docker Compose

```bash
cp .env.example .env
# 编辑 .env，至少填写 JWT_SECRET 和 LLM_API_KEY
docker compose up -d
```

打开：

```text
http://localhost:3077
```

默认账号：

```text
admin@opendocx.local / admin123
```

### 方式二：本地开发

启动数据库后，准备后端：

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
cd ..
bash scripts/seed_demo.sh
bash backend/scripts/start-backend.sh
```

另开终端启动前端：

```bash
cd frontend
npm ci
npx vite --host 0.0.0.0 --port 3077
```

## Demo 数据

执行 `bash scripts/seed_demo.sh` 后会创建：

- 1 个管理员账号：`admin@opendocx.local / admin123`
- 1 个示例项目：`OpenDocX 入门示例`
- 3 篇示例文档：快速开始、AI 浮层示例、Markdown 渲染能力速查

其中 Markdown 渲染示例位于：

```text
examples/markdown-rendering-showcase.md
```

已构建的静态 HTML 展示页位于：

```text
docs/showcase/render-showcase.html
```

线上预览地址：

```text
https://davidwang960707-gpu.github.io/opendocx/showcase/render-showcase.html
```

这份 HTML 已按 GitHub Pages 的 `/docs` 发布目录准备，也可以直接放到其他静态文件服务中展示，用来说明 OpenDocX 静态站对表格、提示块、代码高亮、任务列表、图片、GIF、Mermaid 和公式占位的渲染效果。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | React 18、TypeScript、Ant Design 5、Vite、Zustand |
| 后端 | Python 3.12、FastAPI、SQLAlchemy 2、Alembic |
| 数据库 | PostgreSQL、pgvector |
| 静态站 | mistune、Pygments、自定义 HTML/CSS 构建 |
| 部署 | Docker Compose、Nginx |

## 文档

| 文档 | 内容 |
| --- | --- |
| [用户指南](docs/USER-GUIDE.md) | 从登录、建项目、写文档到构建发布 |
| [API 参考](docs/API.md) | 后端接口说明 |
| [架构说明](docs/ARCHITECTURE.md) | 模块、数据流、构建链路 |
| [产品需求文档](docs/PRD.md) | 产品定位、用户场景和版本范围 |
| [路线图](docs/ROADMAP.md) | v0.1.0 之后的计划 |
| [开源检查清单](docs/OPEN_SOURCE_CHECKLIST.md) | 发布前检查项 |
| [静态站渲染能力速查 HTML](docs/showcase/render-showcase.html) / [线上预览](https://davidwang960707-gpu.github.io/opendocx/showcase/render-showcase.html) | 可直接发布的 Markdown 渲染展示页 |
| [OpenDocX 与 Docusaurus 对标](docs/OpenDocX-vs-Docusaurus-对标报告-2026-06-08.md) | 定位差异和能力边界 |

## v0.1.0-alpha 状态

OpenDocX v0.1.0-alpha 已经具备完整主链路：

- 登录、项目、版本、文档、编辑、发布、构建。
- 反馈审核、用户管理、审计日志。
- Demo seed、Docker Compose、开源文档和截图。

但它仍然是 alpha 版本：

- 前端测试覆盖还不完整。
- 静态站 SEO、站内搜索、媒体资产管理还需要继续增强。
- 多人协作、审批流、实时协同还在路线图中。

## 路线图摘要

- v0.2：静态站阅读体验、搜索、SEO、截图级示例站。
- v0.3：媒体资产管理、Markdown 图片/视频上传、公式和 Mermaid 完整渲染。
- v0.4：团队协作、审批、发布权限和更强审计。
- v1.0：稳定 API、完善测试、生产级部署文档。

详见 [路线图](docs/ROADMAP.md)。

## 贡献

欢迎提交 Issue、PR 和使用反馈。请先阅读：

- [贡献指南](CONTRIBUTING.md)
- [行为准则](CODE_OF_CONDUCT.md)
- [安全策略](SECURITY.md)

## 开源协议

[Apache License 2.0](LICENSE)

## 致谢

OpenDocX 参考和使用了许多优秀开源项目，包括 FastAPI、React、Ant Design、Docusaurus、mistune、Pygments、pgvector 等。感谢这些项目让小团队也能快速搭出可用的产品底座。
