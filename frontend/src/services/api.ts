/** API 服务层 */
import axios from 'axios'
import type {
  ApiResponse, LoginRequest, LoginResponse, User,
  UserFull, UserCreateRequest, UserCreateResponse, UserUpdateRequest,
  UserListResponse, PasswordChangeRequest,
  AuditLog, AuditLogListResponse,
  Project, ProjectCreateRequest, ProjectUpdateRequest,
  Version, VersionCreateRequest,
  Document, DocumentTreeNode, DocumentCreateRequest, DocumentUpdateRequest,
  DocumentAsset,
  SearchRequest, SearchResult,
  DashboardStats, BuildLog,
} from '../types/api'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// 请求拦截：注入 JWT Token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：处理 401
// 关键: 不直接 window.location.href=/login — 那会触发 SPA 路由全跳, 当前 page state 残留
// 改用 React Router navigate + 同步 auth store, 避免数据回包晚到时写入已"过期"组件
let _on401: (() => void) | null = null
export function setApi401Handler(fn: () => void) { _on401 = fn }

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      // 调用 App 层注册的 handler (清 store + navigate('/login')), 避免硬刷
      if (_on401) _on401()
    }
    return Promise.reject(error)
  }
)

// ── 认证 ──────────────────────────────────────────────

export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  getMe: () => api.get('/auth/me'),
  updateMe: (req: { name?: string }) => api.patch<ApiResponse<UserFull>>('/auth/me', req),
}

// ── 项目 ──────────────────────────────────────────────

export const projectApi = {
  list: () => api.get('/projects'),
  get: (id: string) => api.get(`/projects/${id}`),
  create: (data: any) => api.post('/projects', data),
  update: (id: string, data: any) => api.put(`/projects/${id}`, data),
  delete: (id: string) => api.delete(`/projects/${id}`),
}

// ── 版本 ──────────────────────────────────────────────

export const versionApi = {
  list: (projectId: string) => api.get(`/projects/${projectId}/versions`),
  create: (projectId: string, data: any) => api.post(`/projects/${projectId}/versions`, data),
  // R6 反馈 2: 版本管理 UI
  archive: (vid: string) => api.put(`/versions/${vid}/archive`),
  setDefault: (vid: string) => api.put(`/versions/${vid}/default`),
}

// ── 文档 ──────────────────────────────────────────────

export const documentApi = {
  tree: (versionId: string) => api.get(`/versions/${versionId}/documents`),
  get: (id: string) => api.get(`/documents/${id}`),
  create: (versionId: string, data: any) => api.post(`/versions/${versionId}/documents`, data),
  update: (id: string, data: any) => api.put(`/documents/${id}`, data),
  /**
   * R15 预构建弹窗: 批量发布 (走 skip_empty 默认 True, folder 不发布)
   * - 后端: POST /documents/batch-publish
   * - 返回: { published: string[], skipped: {id, reason}[], errors: {id, message}[] }
   */
  batchPublish: (ids: string[], skipEmpty = true) =>
    api.post<ApiResponse<{ published: string[]; skipped: any[]; errors: any[] }>>(
      '/documents/batch-publish', { ids, skip_empty: skipEmpty }
    ),
  delete: (id: string) => api.delete(`/documents/${id}`),
  /**
   * 批量导入本地 Markdown — 调后端 multipart 端点
   * @param versionId 目标 version
   * @param files File[] (浏览器 FileList 转数组)
   */
  importMarkdown: (versionId: string, files: File[]) => {
    const form = new FormData()
    for (const f of files) form.append('files', f, f.name)
    return api.post(`/versions/${versionId}/documents/import`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  // R6 反馈 5: 拖拽排序 — 客户端把整棵树新位置打平
  reorder: (versionId: string, items: { id: string; parent_id: string | null; sort_order: number }[]) =>
    api.post('/documents/reorder', { version_id: versionId, items }),
}

// ── 文档资产 ──────────────────────────────────────────

export const assetApi = {
  list: (versionId: string) =>
    api.get<ApiResponse<DocumentAsset[]>>(`/versions/${versionId}/assets`),
  upload: (versionId: string, file: File) => {
    const form = new FormData()
    form.append('file', file, file.name)
    return api.post<ApiResponse<DocumentAsset>>(`/versions/${versionId}/assets`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    })
  },
  delete: (assetId: string) => api.delete(`/assets/${assetId}`),
}

// ── 搜索 ──────────────────────────────────────────────

export const searchApi = {
  search: (query: string, projectId?: string) =>
    api.post('/search', { query, project_id: projectId, limit: 10 }),
}

// ── 构建 ──────────────────────────────────────────────

export interface BuildManifestItem {
  project_id: string
  project_name: string
  project_slug: string
  brand_color: string
  version_id: string
  version: string
  build_id: string
  built_at: string
  duration: number | null
  doc_count: number
  url: string
}

export const buildApi = {
  trigger: (versionId: string) => api.post(`/build/${versionId}`),
  status: (buildId: string) => api.get(`/build/${buildId}/status`),
  logs: (projectId?: string) => api.get('/build/logs', { params: { project_id: projectId } }),
  latest: (projectId: string, versionId?: string) =>
    api.get('/build/latest', { params: { project_id: projectId, version_id: versionId } }),
  manifest: () => api.get<{ data: BuildManifestItem[]; meta: { count: number } }>('/build/manifest'),
}

// ── 统计 ──────────────────────────────────────────────

export const statsApi = {
  get: () => api.get('/stats'),
}

// ── 系统管理 (P1-W3-A2) ───────────────────────────────

export const userApi = {
  list: (params?: { page?: number; page_size?: number; search?: string; role?: string }) =>
    api.get<UserListResponse>('/users', { params }),
  get: (id: string) => api.get<ApiResponse<UserFull>>(`/users/${id}`),
  create: (req: UserCreateRequest) => api.post<ApiResponse<UserCreateResponse>>('/users', req),
  update: (id: string, req: UserUpdateRequest) => api.patch<ApiResponse<UserFull>>(`/users/${id}`, req),
  delete: (id: string) => api.delete(`/users/${id}`),
  changePassword: (req: PasswordChangeRequest) => api.post<ApiResponse<{ ok: boolean }>>('/auth/change-password', req),
}

export const auditApi = {
  list: (params?: { page?: number; page_size?: number; action?: string; actor_email?: string; target_type?: string }) =>
    api.get<AuditLogListResponse>('/audit-logs', { params }),
}

// ── 反馈 / 评论 (P1-W4-L2) ──────────────────────────

export const feedbackApi = {
  // admin 审核
  adminList: (params?: { kind?: string; document_id?: string; user_email?: string; limit?: number; offset?: number }) =>
    api.get<ApiResponse<any>>('/feedbacks/admin/list', { params }),
  adminDelete: (id: string) => api.delete<ApiResponse<{ deleted: string }>>(`/feedbacks/admin/${id}`),
  // 公开 API (静态站 inline JS 也调, 这里给后台管理面板用)
  listReactions: (docId: string, visitorId: string) =>
    api.get<ApiResponse<any>>(`/feedbacks/${docId}/reactions`, { headers: { 'X-Visitor-Id': visitorId } }),
  listComments: (docId: string) =>
    api.get<ApiResponse<any>>(`/feedbacks/${docId}/comments`),
  create: (payload: any, visitorId: string) =>
    api.post<ApiResponse<any>>('/feedbacks', payload, { headers: { 'X-Visitor-Id': visitorId } }),
  delete: (id: string, visitorId: string) =>
    api.delete<ApiResponse<any>>(`/feedbacks/${id}`, { headers: { 'X-Visitor-Id': visitorId } }),
}

export default api
