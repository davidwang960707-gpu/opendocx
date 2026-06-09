// ── API 通用 ──────────────────────────────────────────

export interface ApiResponse<T = unknown> {
  success: boolean
  data: T
  meta?: PaginationMeta
}

export interface PaginationMeta {
  page: number
  page_size: number
  total: number
  total_pages: number
}

// ── 认证 ──────────────────────────────────────────────

export interface User {
  id: string
  email: string
  name: string
  role: 'admin' | 'editor' | 'viewer'
  created_at: string
}

// P1-W3-A2: 系统管理 — 完整 8 字段 User (含 is_active / last_login_at)
export interface UserFull {
  id: string
  email: string
  name: string
  role: 'admin' | 'editor' | 'viewer'
  is_active: boolean
  last_login_at: string | null
  created_at: string
  updated_at: string
}

export interface UserCreateRequest {
  email: string
  name: string
  role?: 'admin' | 'editor' | 'viewer'
}

export interface UserCreateResponse {
  user: UserFull
  temporary_password: string  // 12 位随机密码, 一次性显示
}

export interface UserUpdateRequest {
  name?: string
  role?: 'admin' | 'editor' | 'viewer'
  is_active?: boolean
}

export interface UserListResponse {
  items: UserFull[]
  total: number
  page: number
  page_size: number
}

export interface PasswordChangeRequest {
  old_password: string
  new_password: string
}

// P1-W3-A2: 审计日志
export interface AuditLog {
  id: string
  actor_id: string | null  // 公开操作 (feedback) 可为 null
  actor_email: string
  action: string
  target_type: string | null
  target_id: string | null
  payload: Record<string, any> | null
  created_at: string
}

export interface AuditLogListResponse {
  items: AuditLog[]
  total: number
  page: number
  page_size: number
}

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

// ── 项目 ──────────────────────────────────────────────

export interface Project {
  id: string
  name: string
  slug: string
  description: string | null
  brand_color: string
  logo_url: string | null
  created_by: string
  created_at: string
  updated_at: string
  // P1-UI-1/2: 服务端注入 (从默认版本 + 文档聚合推导)
  status?: 'active' | 'paused' | 'draft' | null
  default_version_id?: string | null
  doc_count?: number | null
  last_activity_at?: string | null
}

export interface ProjectCreateRequest {
  name: string
  slug: string
  description?: string
  brand_color?: string
}

export interface ProjectUpdateRequest {
  name?: string
  description?: string
  brand_color?: string
  logo_url?: string
}

// ── 版本 ──────────────────────────────────────────────

export interface Version {
  id: string
  project_id: string
  version: string
  is_default: boolean
  status: 'draft' | 'published' | 'archived'
  created_at: string
}

export interface VersionCreateRequest {
  version: string
  is_default?: boolean
}

// ── 文档 ──────────────────────────────────────────────

export interface Document {
  id: string
  version_id: string
  parent_id: string | null
  title: string
  slug: string
  content: string | null
  file_path: string | null
  status: 'draft' | 'published' | 'archived'
  sort_order: number
  created_by: string
  created_at: string
  updated_at: string
}

export interface DocumentTreeNode {
  id: string
  title: string
  slug: string
  status: string
  sort_order: number
  is_folder: boolean  // 后端计算: content 为空 或 有子节点
  /** R7 扩展: 文档内容长度 (folder 时为 0) */
  content_len: number
  /** R7 扩展: 是否有非空内容 */
  has_content: boolean
  children: DocumentTreeNode[]
}

export interface DocumentCreateRequest {
  title: string
  slug: string
  content?: string
  parent_id?: string
  sort_order?: number
}

export interface DocumentUpdateRequest {
  title?: string
  slug?: string
  content?: string
  status?: string
  parent_id?: string
  sort_order?: number
}

// ── 搜索 ──────────────────────────────────────────────

export interface SearchRequest {
  query: string
  project_id?: string
  limit?: number
}

export interface SearchResult {
  document_id: string
  title: string
  content_snippet: string
  score: number
  project_slug: string
  version: string
}

// ── 统计 ──────────────────────────────────────────────

export interface DashboardStats {
  project_count: number
  document_count: number
  published_count: number
}

// ── 构建 ──────────────────────────────────────────────

export interface BuildLog {
  id: string
  project_id: string
  version_id: string
  status: 'pending' | 'building' | 'success' | 'failed'
  output: string | null
  duration: number | null
  triggered_by: string
  created_at: string
}
