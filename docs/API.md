# OpenDocX API 参考

> Base URL: http://localhost:8001/api/v1
>
> 认证: `Authorization: Bearer <token>`（除登录和健康检查外所有端点）

---

## 认证

### POST /auth/login

登录获取 JWT Token。

**请求体：**
```json
{
  "email": "admin@opendocx.local",
  "password": "admin123"
}
```

**响应：**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "token_type": "bearer"
  }
}
```

**错误：**
- 401 — 邮箱或密码错误

---

## 统计

### GET /stats

获取仪表盘统计数据。需要认证。

**响应：**
```json
{
  "success": true,
  "data": {
    "project_count": 2,
    "document_count": 5,
    "published_count": 5
  }
}
```

---

## 项目

### GET /projects

项目列表，支持分页。

**查询参数：**
| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页数量 |

**响应：**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "name": "OpenDocX Demo",
      "slug": "insight",
      "description": "文档智能引擎",
      "brand_color": "#0071e3",
      "logo_url": null,
      "created_by": "uuid",
      "created_at": "2026-06-01T00:00:00",
      "updated_at": "2026-06-01T00:00:00"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 2,
    "total_pages": 1
  }
}
```

### POST /projects

创建项目。需要 admin 或 editor 角色。

**请求体：**
```json
{
  "name": "项目名称",
  "slug": "project-slug",
  "description": "项目描述",
  "brand_color": "#4F46E5"
}
```

### PUT /projects/{id}

更新项目。需要 admin 或 editor 角色。

**请求体：**
```json
{
  "name": "新名称",
  "description": "新描述",
  "brand_color": "#0071e3"
}
```

### DELETE /projects/{id}

删除项目。需要 admin 角色。

---

## 版本

### GET /projects/{pid}/versions

获取项目下的版本列表。

**响应：**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "project_id": "uuid",
      "version": "v1.0",
      "is_default": true,
      "status": "published",
      "created_at": "2026-06-01T00:00:00"
    }
  ]
}
```

### POST /projects/{pid}/versions

创建版本。需要 admin 或 editor 角色。

**请求体：**
```json
{
  "version": "v2.0",
  "is_default": false
}
```

---

## 文档

### GET /versions/{vid}/documents

获取版本下的文档树（树形结构）。

**响应：**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "title": "快速入门",
      "slug": "getting-started",
      "status": "published",
      "sort_order": 1,
      "children": []
    }
  ]
}
```

### POST /versions/{vid}/documents

创建文档。需要 admin 或 editor 角色。

**请求体：**
```json
{
  "title": "文档标题",
  "slug": "doc-slug",
  "content": "# 标题\n\n内容...",
  "parent_id": null,
  "sort_order": 1
}
```

### GET /documents/{did}

获取文档详情。

### PUT /documents/{did}

更新文档。需要 admin 或 editor 角色。

**请求体：**
```json
{
  "title": "新标题",
  "content": "新内容",
  "status": "published",
  "sort_order": 2
}
```

### DELETE /documents/{did}

删除文档。需要 admin 或 editor 角色。

---

## AI 搜索

### POST /search

语义搜索文档。

**请求体：**
```json
{
  "query": "本体设计",
  "project_id": null,
  "limit": 10
}
```

**响应（向量搜索）：**
```json
{
  "success": true,
  "data": [
    {
      "document_id": "uuid",
      "title": "本体设计",
      "content_snippet": "T-Box（术语层）定义业务概念...",
      "score": 0.87,
      "project_slug": "knovax",
      "version": "v1.0"
    }
  ],
  "meta": {
    "method": "vector",
    "model": "BAAI/bge-m3"
  }
}
```

**响应（ILIKE 降级）：**
```json
{
  "success": true,
  "data": [...],
  "meta": {
    "method": "ilike"
  }
}
```

### POST /search/reindex

批量为所有已发布文档生成向量索引。需要 admin 角色。

**响应：**
```json
{
  "success": true,
  "data": {
    "total": 5,
    "success": 5,
    "failed": 0
  }
}
```

---

## 构建

### POST /build/{vid}

触发版本构建。需要 admin 或 editor 角色。

**响应：**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "project_id": "uuid",
    "version_id": "uuid",
    "status": "success",
    "output": "构建成功：5 篇文档，耗时 2s",
    "duration": 2,
    "triggered_by": "uuid",
    "created_at": "2026-06-01T00:00:00"
  }
}
```

### GET /build/{bid}/status

查询构建状态。

### GET /build/logs

获取构建日志列表。

**查询参数：**
| 参数 | 类型 | 说明 |
|---|---|---|
| project_id | string | 按项目筛选 |

## 健康检查

```
GET /health
```

**响应**

```json
{
  "status": "ok",
  "service": "opendocx-backend"
}
```

---

## 编辑器 AI (W1)

6 动作 SSE 流式 (`/api/v1/editor/ai`): 续写 / 改写 / 解释 / Q&A / 总结 / 润色。

```
POST /api/v1/editor/ai
```

**请求体**

```json
{
  "action": "continue",
  "content": "当前文档全文或选区",
  "selection": "选区文本(改写/解释/润色时用)",
  "question": "Q&A 模式的问题",
  "context": { "project_id": "...", "version_id": "...", "title": "..." },
  "temperature": 0.7,
  "max_tokens": 2048
}
```

**响应** — `text/event-stream` (SSE):

```
event: meta
data: {"action": "continue", "model": "mimo-v2.5-pro"}

event: token
data: {"delta": "这是一段"}

event: token
data: {"delta": "续写文本..."}

event: done
data: {"ok": true}
```

**其他端点**:

```
GET  /api/v1/editor/actions   列出 6 动作清单 (前端 AI 浮窗用)
GET  /api/v1/editor/health    检查 LLM provider 配置可用性
```

---

## 公开反馈 (访客)

`POST /api/v1/feedbacks` 公开, 不需要 JWT, 走 `X-Visitor-Id` header 区分访客。

```
POST /api/v1/feedbacks         点赞/点踩/收藏/评论
DELETE /api/v1/feedbacks/{id}  取消 (需 visitor_id 匹配)
GET  /api/v1/feedbacks         列出 (需 JWT, admin 看全部)
```

**请求体**:

```json
{
  "document_id": "uuid",
  "kind": "like | dislike | bookmark | comment",
  "body": "评论内容(仅 comment 必填)",
  "parent_id": "uuid(回复时填)"
}
```

**Header**: `X-Visitor-Id: <uuid>` (浏览器 localStorage 持久化)

---

## 用户管理 (Admin Only)

```
GET    /api/v1/users                   列出所有用户
POST   /api/v1/users                   新建 (返回 12 位临时密码)
GET    /api/v1/users/{id}              详情
PATCH  /api/v1/users/{id}              改角色/姓名
PATCH  /api/v1/users/{id}/active       启用/停用 (软删)
POST   /api/v1/users/{id}/reset        重置密码 (返回新临时密码)
POST   /api/v1/auth/change-password    自己改密码 (需 JWT)
PATCH  /api/v1/auth/me                 改自己姓名 (需 JWT)
```

**响应模型**:

```json
{
  "id": "uuid",
  "email": "user@opendocx.local",
  "name": "姓名",
  "role": "admin | editor | viewer",
  "is_active": true,
  "last_login_at": "2026-06-05T19:58:21",
  "created_at": "2026-05-31T00:00:00"
}
```

---

## 审计日志 (Admin Only)

```
GET /api/v1/audit-logs          列出 (分页 + 过滤)
GET /api/v1/audit-logs/{id}     详情
```

**查询参数**:

| 参数 | 类型 | 说明 |
|---|---|---|
| `page` | int | 页码 (默认 1) |
| `page_size` | int | 每页条数 (默认 20, 最大 100) |
| `actor_email` | str | 按操作人过滤 (支持 `visitor:` 前缀) |
| `action` | str | 按动作过滤 (e.g. `user.create`, `feedback.like`) |
| `resource_type` | str | 按资源类型过滤 (e.g. `user`, `project`, `document`) |

**响应模型**:

```json
{
  "id": 123,
  "actor_id": "uuid or null(访客)",
  "actor_email": "admin@opendocx.local or visitor:abc@visitor",
  "action": "user.update",
  "resource_type": "user",
  "resource_id": "uuid",
  "summary": "1 处改动",
  "changes": {"role": {"old": "viewer", "new": "editor"}},
  "ip_address": "127.0.0.1",
  "created_at": "2026-06-05T19:58:21"
}
```

**已挂 audit hook 的 11 mutation 端点**:

| 端点 | action |
|---|---|
| `POST   /api/v1/auth/login` | `auth.login` |
| `PATCH  /api/v1/auth/me` | `user.update_self` |
| `POST   /api/v1/auth/change-password` | `user.change_password` |
| `POST   /api/v1/users` | `user.create` |
| `PATCH  /api/v1/users/{id}` | `user.update` |
| `PATCH  /api/v1/users/{id}/active` | `user.toggle_active` |
| `POST   /api/v1/users/{id}/reset` | `user.reset_password` |
| `POST   /api/v1/projects` | `project.create` |
| `PATCH  /api/v1/projects/{id}` | `project.update` (含 status 改动) |
| `DELETE /api/v1/projects/{id}` | `project.delete` |
| `POST   /api/v1/projects/{id}/documents` | `document.create` |
| `PATCH  /api/v1/documents/{id}` | `document.update` |
| `DELETE /api/v1/documents/{id}` | `document.delete` |
| `POST   /api/v1/feedbacks` | `feedback.{kind}` (公开, visitor_id) |
| `DELETE /api/v1/feedbacks/{id}` | `feedback.delete` (公开) |

---

## 错误格式

所有错误统一格式：

```json
{
  "detail": "错误描述"
}
```

| HTTP 状态码 | 说明 |
|---|---|
| 400 | 请求参数错误 |
| 401 | 未认证或 Token 过期 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |
