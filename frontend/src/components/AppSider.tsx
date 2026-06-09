/** AppSider — 4 个页面共用的侧栏 (P1 统一色系)
 *
 * 4 个页面 (Dashboard/Projects/Documents/Published) 共用一个侧栏：
 * - 240px 宽
 * - Logo + 副标题
 * - 4 个主菜单 (概览/项目管理/已发布/编辑器按需)
 * - 底部状态条 (AI 助手 / 主题切换)
 * - 颜色统一用 --sider-* token
 */
import { ReactNode } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Menu, Typography, Space, Avatar, Dropdown, Button, Tooltip } from 'antd'
import {
  DashboardOutlined, ProjectOutlined, GlobalOutlined, FileTextOutlined,
  UserOutlined, LogoutOutlined, SunOutlined, MoonOutlined, DesktopOutlined,
  TeamOutlined, HistoryOutlined, SettingOutlined, SafetyOutlined,
  CommentOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '../stores/auth'
import { useThemeStore } from '../stores/theme'

const { Text } = Typography

const THEME_ICON = {
  light: <SunOutlined />,
  dark: <MoonOutlined />,
  system: <DesktopOutlined />,
}
const THEME_LABEL = {
  light: '浅色',
  dark: '深色',
  system: '跟随系统',
}

interface AppSiderProps {
  /** 子标题（默认为"AI 项目文档与发布平台"） */
  subtitle?: string
  /** 当前路由前缀（用于菜单高亮），默认自动从 location.pathname 推断 */
  activeKey?: string
  /** 顶部 Logo 下方插入内容（项目选择器、版本选择器等） */
  topSlot?: ReactNode
  /** 菜单下方插入内容（编辑器 Tree 等） */
  middleSlot?: ReactNode
  /** 底部"AI 助手"上方插入内容（任意 footer 信息） */
  bottomSlot?: ReactNode
  /** 是否显示底部 AI 助手状态条 */
  showFooter?: boolean
}

/** 4 个页面共享的菜单项定义 (P1-W3-A4: 加 [系统管理] 段 admin-only) */
const DEFAULT_MENU = [
  { key: '/',           icon: <DashboardOutlined />, label: '概览' },
  { key: '/projects',   icon: <ProjectOutlined />,    label: '项目管理' },
  { key: '/published',  icon: <GlobalOutlined />,     label: '已发布' },
] as const

/** P1-W3-A4: 系统管理段 — admin-only (3 子项, P1-W4-L2 加反馈审核) */
const ADMIN_MENU = [
  { key: '/admin/users',     icon: <TeamOutlined />,     label: '用户管理' },
  { key: '/admin/audit',     icon: <HistoryOutlined />,  label: '审计日志' },
  { key: '/admin/feedbacks', icon: <CommentOutlined />,  label: '反馈审核' },
] as const

function pickActiveKey(pathname: string): string {
  if (pathname === '/') return '/'
  if (pathname.startsWith('/projects')) return '/projects'
  if (pathname.startsWith('/published')) return '/published'
  if (pathname.startsWith('/admin/users')) return '/admin/users'
  if (pathname.startsWith('/admin/audit')) return '/admin/audit'
  if (pathname.startsWith('/admin/feedbacks')) return '/admin/feedbacks'
  if (pathname.startsWith('/settings')) return '/settings'
  return ''
}

export default function AppSider({
  subtitle = 'AI 项目文档与发布平台',
  activeKey,
  topSlot,
  middleSlot,
  bottomSlot,
  showFooter = true,
}: AppSiderProps) {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()
  const themeMode = useThemeStore(s => s.mode)
  const cycleTheme = useThemeStore(s => s.cycle)

  const selected = activeKey ?? pickActiveKey(location.pathname)
  const isAdmin = user?.role === 'admin'
  const userMenu = {
    items: [
      { key: 'profile', icon: <SettingOutlined />, label: '个人设置', onClick: () => navigate('/settings') },
      { type: 'divider' as const },
      { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true, onClick: () => { logout(); navigate('/login') } },
    ],
  }
  const userMenuLabel = (
    <Space size={6} style={{ padding: '4px 0' }}>
      <Text style={{ fontSize: 12 }}>{user?.name || user?.email}</Text>
      {isAdmin && (
        <Text style={{ fontSize: 10, color: 'var(--brand-color, #4F46E5)' }}>· 管理员</Text>
      )}
    </Space>
  )

  return (
    <aside className="app-sider">
      {/* === Logo 区 === */}
      <div className="app-sider-brand">
        <div className="app-sider-logo">
          <div className="app-sider-logo-mark">O</div>
          <Text className="app-sider-logo-text">OpenDocX</Text>
        </div>
        {subtitle && <Text className="app-sider-subtitle">{subtitle}</Text>}
        {topSlot && <div className="app-sider-top-slot">{topSlot}</div>}
      </div>

      {/* === 主菜单 (P1-W3-A4: 加 admin 角色时显示 [系统管理] 段) === */}
      <Menu
        className="app-sider-menu"
        mode="inline"
        theme="dark"
        selectedKeys={selected ? [selected] : []}
        items={[
          ...(DEFAULT_MENU as any),
          ...(isAdmin
            ? [{ type: 'group' as const, key: 'admin-group', label: '系统管理', children: ADMIN_MENU as any }]
            : []),
        ]}
        onClick={({ key }) => navigate(key as string)}
      />

      {/* === 中部自定义内容（项目选择器、Tree 等） === */}
      {middleSlot && <div className="app-sider-middle-slot">{middleSlot}</div>}

      {/* === 底部 === */}
      <div className="app-sider-footer">
        {bottomSlot}
        {showFooter && (
          <>
            <Space size={6} className="app-sider-status">
              <span className="app-sider-status-dot" />
              <Text className="app-sider-status-text">AI 助手 Atlas 在线</Text>
            </Space>
            <Space size={4} className="app-sider-actions">
              <Tooltip title={`主题：${THEME_LABEL[themeMode]}（点击切换）`}>
                <Button
                  type="text"
                  size="small"
                  icon={THEME_ICON[themeMode]}
                  onClick={cycleTheme}
                  data-testid="sider-theme-toggle"
                  className="app-sider-action-btn"
                />
              </Tooltip>
              <Dropdown menu={userMenu} placement="topRight" trigger={['click']}>
                <Avatar
                  size={28}
                  className="app-sider-avatar"
                  data-testid="sider-user-avatar"
                  style={{ cursor: 'pointer' }}
                >
                  {user?.name?.[0] || <UserOutlined />}
                </Avatar>
              </Dropdown>
            </Space>
          </>
        )}
      </div>
    </aside>
  )
}
