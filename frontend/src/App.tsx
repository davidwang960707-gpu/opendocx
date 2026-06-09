import { useEffect, useState, useCallback, useContext, createContext, useMemo, useRef } from 'react'
import { Routes, Route, Navigate, useNavigate, useParams } from 'react-router-dom'
import { Spin } from 'antd'
import {
  DashboardOutlined, ProjectOutlined, GlobalOutlined, LogoutOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { useAuthStore } from './stores/auth'
import { setApi401Handler } from './services/api'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Projects from './pages/Projects'
import ProjectOverview from './pages/ProjectOverview'
import Documents from './pages/Documents'
import Published from './pages/Published'
import AdminUsers from './pages/AdminUsers'
import AdminAudit from './pages/AdminAudit'
import AdminFeedbacks from './pages/AdminFeedbacks'
import Settings from './pages/Settings'
import CommandPalette, { type Command } from './components/CommandPalette'
import { projectApi } from './services/api'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuthStore()
  if (loading) return <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: '40vh' }} />
  if (!user) return <Navigate to="/login" />
  return <>{children}</>
}

// P1-W3-A4: admin-only 路由包装 (非 admin 角色跳 / 概览)
function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuthStore()
  if (loading) return <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: '40vh' }} />
  if (!user) return <Navigate to="/login" />
  if (user.role !== 'admin') return <Navigate to="/" replace />
  return <>{children}</>
}

// Admin R13: /projects/:id 重定向到 /docs (用 useParams 解出 :projectId 拼新路径)
function RedirectToProjectDocs() {
  const { projectId } = useParams<{ projectId: string }>()
  return <Navigate to={`/projects/${projectId}/docs`} replace />
}

// ── Command Palette Context ──────────────────────────
interface CPContextValue {
  open: boolean
  setOpen: (v: boolean) => void
  registerCommands: (id: string, cmds: Command[]) => () => void
}
const CommandPaletteContext = createContext<CPContextValue | null>(null)

export function useCommandPaletteApi() {
  const ctx = useContext(CommandPaletteContext)
  if (!ctx) throw new Error('useCommandPaletteApi must be used within App')
  return ctx
}

export function useRegisterCommands(id: string, cmds: Command[]) {
  const { registerCommands } = useCommandPaletteApi()
  useEffect(() => {
    return registerCommands(id, cmds)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, JSON.stringify(cmds.map(c => c.id))])
}

export default function App() {
  const { checkAuth, user, logout } = useAuthStore()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  // dynamic commands: id -> cmds（页面卸载时通过 unregister 移除）
  const [dynamic, setDynamic] = useState<Record<string, Command[]>>({})
  const registerCommands = useCallback((id: string, cmds: Command[]) => {
    setDynamic(d => ({ ...d, [id]: cmds }))
    return () => setDynamic(d => {
      const { [id]: _, ...rest } = d
      return rest
    })
  }, [])

  // 注册 axios 401 处理器 — 任何 API 返 401 时清 store + navigate('/login')
  // 避免 window.location.href 硬刷导致 React state 残留
  useEffect(() => {
    setApi401Handler(() => {
      logout()
      navigate('/login', { replace: true })
    })
    return () => setApi401Handler(() => {})
  }, [logout, navigate])

  // 静态命令
  const staticCommands: Command[] = useMemo(() => [
    {
      id: 'nav.dashboard', label: '前往概览', group: '导航',
      keywords: ['首页', 'home', 'dashboard'], shortcut: 'G H',
      icon: <DashboardOutlined />, run: () => navigate('/'),
    },
    {
      id: 'nav.projects', label: '前往项目管理', group: '导航',
      keywords: ['项目', 'project'], shortcut: 'G P',
      icon: <ProjectOutlined />, run: () => navigate('/projects'),
    },
    {
      id: 'nav.published', label: '查看已发布站点', group: '导航',
      keywords: ['发布', '构建', 'published', 'build'],
      icon: <GlobalOutlined />, run: () => navigate('/published'),
    },
    {
      id: 'op.refresh', label: '刷新当前页', group: '操作',
      keywords: ['reload', '刷新'],
      icon: <ReloadOutlined />, run: () => window.location.reload(),
    },
    {
      id: 'op.logout', label: '退出登录', group: '操作',
      keywords: ['logout', '退出', 'sign out'],
      icon: <LogoutOutlined />, run: () => { logout(); navigate('/login') },
    },
  ], [navigate, logout])

  // 动态：列出最近项目
  const [projectCmds, setProjectCmds] = useState<Command[]>([])
  useEffect(() => {
    if (!user) { setProjectCmds([]); return }
    let alive = true
    projectApi.list().then((res) => {
      if (!alive) return
      const projects: any[] = res.data?.data || []
      setProjectCmds(projects.slice(0, 10).map((p) => ({
        id: `nav.project.${p.id}`,
        label: `打开项目：${p.name}`,
        group: '项目' as const,
        keywords: ['项目', 'project', p.slug, p.name],
        icon: <ProjectOutlined />,
        run: () => navigate(`/projects/${p.id}/docs`),
      })))
    }).catch(() => {})
    return () => { alive = false }
  }, [user, navigate])

  const allCommands = useMemo(() => [
    ...staticCommands,
    ...projectCmds,
    ...Object.values(dynamic).flat(),
  ], [staticCommands, projectCmds, dynamic])

  // ⌘K / Ctrl+K 唤出
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setOpen(o => !o)
      } else if (e.key === 'Escape' && open) {
        setOpen(false)
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  // P1-W1-D-4: 监听 'opendocx:open-palette' 自定义事件 (Dashboard ⌘K 按钮)
  useEffect(() => {
    const onPalette = () => setOpen(true)
    window.addEventListener('opendocx:open-palette', onPalette)
    return () => window.removeEventListener('opendocx:open-palette', onPalette)
  }, [])

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  const ctxValue = useMemo(() => ({ open, setOpen, registerCommands }), [open, registerCommands])

  return (
    <CommandPaletteContext.Provider value={ctxValue}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
        <Route path="/projects" element={<PrivateRoute><Projects /></PrivateRoute>} />
        {/* Admin R13: /projects/:id 重定向到 /docs (overview 内容已嵌进 /docs 没选状态) */}
        <Route path="/projects/:projectId" element={<PrivateRoute><RedirectToProjectDocs /></PrivateRoute>} />
        <Route path="/projects/:projectId/docs" element={<PrivateRoute><Documents /></PrivateRoute>} />
        <Route path="/published" element={<PrivateRoute><Published /></PrivateRoute>} />
        {/* P1-W3-A2: 系统管理 (admin-only) */}
        <Route path="/admin/users" element={<AdminRoute><AdminUsers /></AdminRoute>} />
        <Route path="/admin/audit" element={<AdminRoute><AdminAudit /></AdminRoute>} />
        {/* P1-W4-L2: 反馈审核 (admin/editor) */}
        <Route path="/admin/feedbacks" element={<AdminRoute><AdminFeedbacks /></AdminRoute>} />
        {/* P1-W3-A3: 个人设置 (任何人) */}
        <Route path="/settings" element={<PrivateRoute><Settings /></PrivateRoute>} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
      <CommandPalette open={open} onClose={() => setOpen(false)} commands={allCommands} />
    </CommandPaletteContext.Provider>
  )
}
