import { ReactNode, useEffect, useRef, useState, useCallback } from 'react'
import { Space, Button, Tooltip } from 'antd'
import { SunOutlined, MoonOutlined, DesktopOutlined } from '@ant-design/icons'
import { useThemeStore } from '../stores/theme'
import LocaleSwitcher from '../i18n/LocaleSwitcher'
import AppSider from '../components/AppSider'

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

const SIDER_MIN = 200
const SIDER_MAX = 400
const SIDER_DEFAULT = 240
const SIDER_STORAGE_KEY = 'opendocx.siderWidth'

interface MainLayoutProps {
  children: ReactNode
  title?: string
  headerLeft?: ReactNode
  headerRight?: ReactNode
  /** 隐藏页头 (Documents 三栏页有自己的 header) */
  hideHeader?: boolean
  /** AppSider 顶部 slot (在 logo + subtitle 下方插入内容, 例如项目上下文) */
  topSlot?: ReactNode
  /** P1-段1 W1 修 1.0 既存错: AppSider 副标题 (默认 "AI 文档平台") */
  subtitle?: string
  /** 数据密集页面可放宽内容区，默认保持 1200px 阅读宽度 */
  contentMaxWidth?: number | 'full'
}

function loadSiderWidth(): number {
  try {
    const v = localStorage.getItem(SIDER_STORAGE_KEY)
    if (v) {
      const n = Number(v)
      if (n >= SIDER_MIN && n <= SIDER_MAX) return n
    }
  } catch {}
  return SIDER_DEFAULT
}

export default function MainLayout({
  children,
  title,
  headerLeft,
  headerRight,
  hideHeader,
  topSlot,
  subtitle,
  contentMaxWidth = 1200,
}: MainLayoutProps) {
  const themeMode = useThemeStore(s => s.mode)
  const cycleTheme = useThemeStore(s => s.cycle)
  const [siderWidth, setSiderWidth] = useState<number>(() => loadSiderWidth())
  const [dragging, setDragging] = useState(false)
  const dragStateRef = useRef<{ startX: number; startW: number } | null>(null)

  const onResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    dragStateRef.current = { startX: e.clientX, startW: siderWidth }
    setDragging(true)
  }, [siderWidth])

  useEffect(() => {
    if (!dragging) return
    const onMove = (e: MouseEvent) => {
      const s = dragStateRef.current
      if (!s) return
      const dx = e.clientX - s.startX
      const next = Math.min(SIDER_MAX, Math.max(SIDER_MIN, s.startW + dx))
      setSiderWidth(next)
    }
    const onUp = () => {
      setDragging(false)
      dragStateRef.current = null
    }
    document.body.classList.add('sider-resizing')
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
    return () => {
      document.body.classList.remove('sider-resizing')
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
  }, [dragging])

  // 拖拽结束后持久化
  useEffect(() => {
    if (!dragging) {
      try { localStorage.setItem(SIDER_STORAGE_KEY, String(siderWidth)) } catch {}
    }
  }, [dragging, siderWidth])

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: `${siderWidth}px 1fr`,
        minHeight: '100vh',
        background: 'var(--bg-primary)',
      }}
    >
      <div style={{ position: 'relative' }}>
        <AppSider subtitle={subtitle ?? title} topSlot={topSlot} />
        <div
          className={`sider-resize-handle${dragging ? ' dragging' : ''}`}
          onMouseDown={onResizeStart}
          data-testid="sider-resize-handle"
          aria-label="拖拽调整侧栏宽度"
          role="separator"
        />
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0, minHeight: 0 }}>
        {!hideHeader && (
          <div style={{
            background: 'var(--bg-overlay)',
            padding: '0 32px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid var(--border-subtle)',
            height: 56,
            flexShrink: 0,
          }}>
            <div>{headerLeft}</div>
            <Space>
              {headerRight}
              <LocaleSwitcher />
              <Tooltip title={`主题：${THEME_LABEL[themeMode]}（点击切换）`}>
                <Button
                  type="text"
                  size="small"
                  icon={THEME_ICON[themeMode]}
                  onClick={cycleTheme}
                  data-testid="header-theme-toggle"
                />
              </Tooltip>
            </Space>
          </div>
        )}

        <div
          style={{
            padding: hideHeader ? 0 : 32,
            flex: 1,
            minHeight: 0,
            overflow: 'auto',
            background: 'var(--bg-primary)',
          }}
        >
          {!hideHeader && (
            <div
              style={{
                width: '100%',
                maxWidth: contentMaxWidth === 'full' ? 'none' : contentMaxWidth,
                margin: contentMaxWidth === 'full' ? 0 : '0 auto',
              }}
            >
              {children}
            </div>
          )}
          {hideHeader && children}
        </div>
      </div>
    </div>
  )
}
