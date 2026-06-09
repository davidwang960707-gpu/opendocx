# Changelog

本项目所有变更记录于此。格式基于 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
版本号遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)。

## [Unreleased]

### Planned
- R16 静态站 AI 浮层 + 批注 (maintainer待研究后定)
- Live demo URL (Vercel/Railway)
- Hacker News 投递 + 中文圈技术媒体

---

## [0.1.0] - 2026-06-08

首个公开 alpha 版。**核心能力 + 完整 4 月开发周期收口 release**。

### Highlights
- **AI 原生三栏编辑器**:Markdown 编辑器 + 实时预览 + AI 助手侧栏
- **AI 浮层 (F1)**: 选区文字 → 6 种 AI 操作 (摘要/扩写/翻译/qa/分析/改写), 流式 SSE
- **预构建弹窗**: 构建前看 doc 树, 单/批量发布, 草稿检测
- **静态站生成**: mistune 3 + pygments 13 lang + Mermaid + Admonition + dark mode
- **Web 管理后台**: 11 个页面 / Dashboard / 用户管理 / 审计日志 / 反馈审核
- **AI 增强**: 3 栏布局 / ⌘K Command Palette / Dashboard 2.0 / Dark mode / 多语言
- **完整 RBAC**: admin / editor / viewer 3 角色 + 11 个 mutation 审计
- **端到端 R7-R15 polish**: 14 段迭代, 0 mock 数据

### Statistics (v0.1.0)
- **代码量**: 15,464 LOC (Python 6,567 + TypeScript/TSX 8,897)
- **测试**: 10 个 pytest 文件 (后端) + 0 前端测试 (待补)
- **Commits**: 78
- **Contributors**: 1 (maintainer + Claude Code 协作)
- **构建产物**: 11 个项目目录, 73 个 .html 静态页
- **截图**: 58 张 (docs/screenshots/)

### Added
- **P0 核心 (Feb-May 2026)**
  - FastAPI 后端 + React/TypeScript 前端 基础架构
  - PostgreSQL + pgvector 向量检索
  - JWT 认证 + RBAC (admin/editor/viewer)
  - LLM provider 抽象 (OpenAI / Hermes / 小米 mimo)
  - 三栏 Markdown 编辑器 (Editor + Preview + AI Panel)
  - 6 种 AI 操作 (SSE 流式): summarize / expand / translate / qa / analyze / rewrite
  - ⌘K 全局命令面板
  - 5 段底部状态栏
  - AI 浮层 (R0-B-5)
  - 静态站生成 (mistune 3 + pygments + bleach)
  - `/published` 页 + manifest endpoint
- **P1 段 1 (W1-W2, 2026-05)**
  - Dashboard 2.0 (今天顶卡 + 7d sparkline + 3 段流)
  - Projects 重设计 (列表/网格 toggle + 状态矩阵)
  - Local Markdown 批量上传
  - ⌘K 接真搜索 (embedding 检索)
- **P1 段 2 (W2-W3, 2026-05)**
  - 项目卡 hover 3 复制 icon + toast
  - Drawer 新建项目 (3 模板 + seed 文档)
  - inline 状态列编辑 (乐观更新)
  - 我的项目 / 全部项目 Tab
- **P1 段 3 (W3, 2026-05)**
  - 用户管理 6 端点 + 改密码
  - 11 个 mutation 挂 audit hook
  - /admin/users + /admin/audit 页面
  - 前端 /settings 3 段
- **P1 段 4 (W4, 2026-06)**
  - 侧栏 [系统管理] 段 + AdminRoute RBAC
  - 头像下拉
  - /admin/feedbacks 反馈审核页
  - F2 anti-spam 4 件套
  - F3 嵌套回复
  - 15 BUG 修复 (BUG-7/10/11/12/13/14/15)
- **P1 段 5 (W5, 2026-06)**
  - Atlas EIDS 9 色 + 玻璃感
  - 浅色侧栏浅灰 + divide-y
  - 状态矩阵 + 审计序号
  - 6 档呼吸感
  - 12/12 E2E probe + 6 截图 + 收工总结
  - C5 i18n 中英切换
  - C7 Folder 跳过 + C8 项目级 _config.yml
- **V2 视觉整改 (2026-06-04)**
  - 管理后台视觉整改 (Dashboard + 侧栏 + 暗色紫调)
  - 悬浮胶囊 + 二级菜单
  - 17 件 UI 强化
- **R 整改 (2026-06-05)**
  - 17 件 UI 强化合并
- **R7-R15 Polish (2026-06-06/07/08, 8 段 7 commits)**
  - R7 4 修: import 自动发布 + list content_len + Mermaid 渲染 + 深色 CSS 隔离
  - R8: 5 种 Admonition 提示块 (GitHub/Obsidian 风格)
  - R9: content-inner 760→920px (+19% 内容宽度)
  - R10: H2 段前 hr 取消 + H4-H6 跟正文 + 媒体 demo + 语法注脚
  - R10 后置: /projects 列表 500 fix (默认版本去重, published 优先)
  - R11: ai-floating-tip 内联 query 输入框
  - R12: LLM_API_KEY 配置 fail-fast + 清晰 503 错误 + start-backend auto-source .env
  - R13: qa 选区上下文 + 接受替换精确位置
  - R14: 64 文档批量导入 vibe-coding-book
  - R15: 预构建弹窗 + 批量发布 (单/批量) + 草稿检测
- **Docs (2026-06-08)**
  - OpenDocX vs Docusaurus 对标报告 (10458 bytes, 168 行, commit d8c5d04)
  - R14 收工 - 64 文档批量导入 (3429 bytes, commit ad4aca8)
  - 收工总结 2026-06-07 llm-causal (6731 bytes)

### Fixed
- R7 修 4 反馈 (import 自动发布 / list content_len / Mermaid 渲染 / 深色 CSS 隔离)
- R8 修 Admonition 块不起眼问题
- R9 修 760px 内容窄, 1024-1280 屏留白多
- R10 修 H2 段前 hr 太多 + H4-H6 字号跟正文一样大
- R10 后置修 /projects 500 (MultipleResultsFound)
- R11 修 AI 浮层没 Modal 没出根因
- R12 修 LLM_API_KEY 占位符导致 AI 编辑全 fail
- R13 修 qa 模式没把 selection 送进 LLM + 接受替换走末尾追加
- R15 修构建按钮被 `selectedDoc &&` 包住导致 version 级按钮失效

### Security
- R12 起 LLM_API_KEY 4 层 fail-fast 校验
- mistune.escape=True + bleach 转义内联 HTML
- JWT 7 天过期 + 401 不硬刷
- audit_logs 11 个 mutation 端点全覆盖

### Changed
- 重写 .gitignore (Python + Node + .env + Hermes session cache)
- start-backend.sh 改为 auto-source .env (R12)
- 端口约定: 后端 8001, 前端 3077 (避免常见端口冲突)

### Deprecated
无

### Removed
- 默认 Markdown 不再用无保护的 html.raw

---

## 开发阶段 (v0.1.0 之前)

### P0 (2026-02 ~ 2026-04)
- 6bb33c6 initial commit (post-mordor)
- 基础架构: FastAPI + React 18 + PostgreSQL + pgvector
- 5f7d463 底部状态栏
- 2576a73 AI 浮层 popup
- 95f6853 三栏布局 + AI 面板
- 16f7e55 SSE streaming + 6 AI actions
- 15cd117 LLM provider 抽象
- 5fb4c2f create_project auto-creates v1.0
- 046a4c5 add 4 e2e tests for build flow
- b67006a force UTC + Z suffix
- 2b98560 /published page with manifest
- 8e3b821 /api/v1/build/latest + manifest endpoints
- 1878cb1 comprehensive markdown rendering
- 6408c13 remove duplicate H1
- fee4d14 split schemas/__init__.py into 6 domain files

### P1 段 1 (2026-05 W1-W2, 7 commits)
- 8a40eda ⌘K 接真搜索
- 83e2469 Dashboard 2.0 3 段流
- bb4ccfa Dashboard 2.0 今天顶卡
- 4b1dfd1 本地 Markdown 批量上传
- 9e51897 Dashboard redesign
- c6d3df0 Projects redesign + dark mode
- c6ff0dd ⌘K global command palette

### P1 段 2 (W2, 5 commits)
- 8a40eda ⌘K embedding search
- d14d830 P-2 status 真存 + P-1 列表/网格 toggle
- dafbbb5 inline 状态列编辑
- 064bead 状态矩阵 4 段收折 + Tab
- 21edef5 项目卡 hover 3 复制 icon
- 138af31 Drawer 新建项目 + 3 模板

### P1 段 3 (W3, 4 commits)
- 9c2bb0a 用户管理 6 端点
- 9712c5b audit hook
- 2271d3a /admin/users 列表
- 0179482 /settings 3 段
- 9dc91e5 侧栏 [系统管理] 段

### P1 段 4 (W4, 3 commits)
- 7558be2 F3 嵌套回复 + BUG-7/12/15
- 0c68040 F2 anti-spam 4 件套 + BUG-10/11/13/14
- ac24eea /admin/feedbacks 反馈审核页

### P1 段 5 (W5, 4 commits)
- 56f44a5 段 4 收工 E2E + 6 截图
- dcc6c24 C7 Folder 跳过 + C8 _config.yml
- 1ac8495 C6 Hero 跳过说明
- 2d505f0 C5 i18n 中英切换

### V2 + R 整改 (2026-06-04/05, 3 commits)
- 9cf893e V2-A 管理后台视觉整改
- 938d121 V2-A + V2-B + V2-C
- f3e6433 6 件产品文档全量更新
- f4892b5 R 整改延期合并

### P0-legacy (W2, 1 commit)
- 4974fcd pgvector 扩展 + document.delete 修底

### R7-R15 Polish (2026-06-06/07/08, 8 commits)
- 2200a83 R7 4 修
- 7405e40 R8 Admonition
- f4ab801 R9 content-inner 920
- 0b02885 R10 H2/H4-H6/媒体
- 980504d /projects 500 fix
- 51991a2 R11 AI 浮层输入
- d00c05d R12 LLM fail-fast
- 25e40df R12 start-backend auto-source
- 69e8817 R13 qa 选区 + 接受替换
- ad4aca8 R14 64 文档批量
- b2d8114 R15 预构建弹窗

### 对标 + 收工 (2026-06-08, 1 commit)
- d8c5d04 OpenDocX vs Docusaurus 对标报告

---

## 版本号约定

- **0.x.y**: Pre-1.0 开发期,API 可能变化
- **x.0.0**: 重大重构,可能不向后兼容
- **x.y.0**: 新功能
- **x.y.z**: 修 bug

项目协作规则 v3 #3: 修+验证 一次 commit 收; commit message 必含真根因 + 估时。

---

[Unreleased]: https://github.com/<your-org>/opendocx/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/<your-org>/opendocx/releases/tag/v0.1.0
