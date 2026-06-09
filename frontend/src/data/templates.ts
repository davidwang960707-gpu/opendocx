/** 项目模板 — 新建项目 Drawer 选模板
 *
 * 3 个内置模板:
 * - blank      空白项目, 只填 name+slug+description+brand_color
 * - api-doc    API 文档模板, 预填 description + 自动创 v1.0 / {api-guide.md}
 * - getting-started  入门指南模板, 预填 description + 自动创 {quickstart.md, concepts.md}
 *
 * 数据流:
 * 1. 用户选模板 → ProjectTemplate 写入 Form
 * 2. 提交时, 如果 template.kind !== 'blank', 调后端 /api/v1/versions/{vid}/documents 创 seed 文档
 * 3. 模板里 slug 字段名 (api-doc / getting-started) 跟 Project.slug 是 2 个概念
 *    — template.slug 是模板标识, Project.slug 是用户填的项目标识
 */

export type TemplateKind = 'blank' | 'api-doc' | 'getting-started'

export interface ProjectTemplate {
  kind: TemplateKind
  name: string
  description: string
  /** 默认 description, 用户可改 */
  defaultDescription: string
  /** 默认 brand color */
  defaultColor: string
  /** 模板描述 (Drawer 卡片副标题) */
  blurb: string
  /** seed 文档列表 (kind !== blank 时调 documents.create 创) */
  seeds: Array<{ slug: string; title: string; content: string }>
}

const API_GUIDE_MD = `# API 认证指南

本章节介绍 OpenDocX 平台的 API 认证机制。

## 1. 获取 API Key

在控制台 \`设置 → API Key\` 生成你的 API Key。

\`\`\`bash
curl -H "Authorization: Bearer YOUR_API_KEY" \\
  https://api.opendocx.com/v1/projects
\`\`\`

## 2. JWT Token

除 API Key 外, 平台支持 JWT 短期 token (1h 过期)。

| 认证方式 | 适用场景 | 有效期 |
|---|---|---|
| API Key | 后端服务 | 长期 |
| JWT | 前端 SPA | 1h |

## 3. 错误码

| HTTP | 含义 |
|---|---|
| 401 | 未认证 / token 过期 |
| 403 | 无权限 |
| 429 | 限流 |
`

const QUICKSTART_MD = `# 快速开始

5 分钟上手 OpenDocX 平台。

## 第 1 步: 注册

访问 [opendocx.com/signup](https://opendocx.com/signup) 注册账号。

## 第 2 步: 创建项目

控制台首页 → \`新建项目\` → 选模板。

## 第 3 步: 集成 SDK

\`\`\`bash
npm install @opendocx/sdk
\`\`\`

\`\`\`javascript
import { OpenDocX } from '@opendocx/sdk'
const client = new OpenDocX({ apiKey: process.env.KNOVAX_API_KEY })
const projects = await client.projects.list()
\`\`\`

## 第 4 步: 部署

\`\`\`bash
npx opendocx deploy
\`\`\`
`

const CONCEPTS_MD = `# 核心概念

理解 OpenDocX 平台的 4 个核心概念。

## 项目 (Project)

项目的顶层容器, 包含文档、版本、构建。

## 版本 (Version)

项目可以有多个版本 (v1.0, v1.1, v2.0), 每个版本独立构建。

## 文档 (Document)

Markdown 源文件, 一个文档 = 一个 .md。

## 构建 (Build)

把 Markdown 编译成静态 HTML, 输出到 /docs/{slug}/{version}/。
`

export const PROJECT_TEMPLATES: ProjectTemplate[] = [
  {
    kind: 'blank',
    name: '空白项目',
    description: '从零开始',
    defaultDescription: '',
    defaultColor: '#4F46E5',
    blurb: '只创建项目和默认版本 v1.0, 不预置任何文档',
    seeds: [],
  },
  {
    kind: 'api-doc',
    name: 'API 文档',
    description: '适合 API 参考手册',
    defaultDescription: 'RESTful API 接口参考与调用示例',
    defaultColor: '#0EA5E9',
    blurb: '预置认证指南文档, 自动生成 1 篇 seed 文档',
    seeds: [
      { slug: 'api-guide', title: 'API 认证指南', content: API_GUIDE_MD },
    ],
  },
  {
    kind: 'getting-started',
    name: '入门指南',
    description: '适合新用户上手',
    defaultDescription: '面向新用户的快速开始和核心概念介绍',
    defaultColor: '#10B981',
    blurb: '预置快速开始 + 核心概念, 自动生成 2 篇 seed 文档',
    seeds: [
      { slug: 'quickstart', title: '快速开始', content: QUICKSTART_MD },
      { slug: 'concepts', title: '核心概念', content: CONCEPTS_MD },
    ],
  },
]

export function getTemplate(kind: TemplateKind): ProjectTemplate {
  return PROJECT_TEMPLATES.find(t => t.kind === kind) || PROJECT_TEMPLATES[0]
}
