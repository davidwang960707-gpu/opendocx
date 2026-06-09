/** 主题状态 — P1-UI-5
 *
 * 支持：
 * - 'light' | 'dark' | 'system'
 * - 持久化到 localStorage
 * - 'system' 跟随 OS prefers-color-scheme
 * - 监听 OS 主题切换自动更新
 */
import { create } from 'zustand'

type ThemeMode = 'light' | 'dark' | 'system'

interface ThemeState {
  mode: ThemeMode
  effective: 'light' | 'dark'  // 实际生效的（mode=system 时取 OS）
  setMode: (m: ThemeMode) => void
  cycle: () => void  // 快捷：light -> dark -> system -> light
}

function getSystemPref(): 'light' | 'dark' {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(effective: 'light' | 'dark') {
  const root = document.documentElement
  root.setAttribute('data-theme', effective)
  // AntD 5: 改 ConfigProvider 主题需 React 重新渲染
  // 我们用 data-theme 给 CSS 变量兜底
}

function loadInitial(): { mode: ThemeMode; effective: 'light' | 'dark' } {
  if (typeof window === 'undefined') return { mode: 'system', effective: 'light' }
  const saved = localStorage.getItem('opendocx-theme') as ThemeMode | null
  const mode: ThemeMode = saved || 'system'
  const effective = mode === 'system' ? getSystemPref() : mode
  applyTheme(effective)
  return { mode, effective }
}

const initial = loadInitial()

export const useThemeStore = create<ThemeState>((set, get) => ({
  mode: initial.mode,
  effective: initial.effective,

  setMode: (m) => {
    const effective = m === 'system' ? getSystemPref() : m
    localStorage.setItem('opendocx-theme', m)
    applyTheme(effective)
    set({ mode: m, effective })
  },

  cycle: () => {
    const order: ThemeMode[] = ['light', 'dark', 'system']
    const cur = get().mode
    const next = order[(order.indexOf(cur) + 1) % order.length]
    get().setMode(next)
  },
}))

// 监听 OS 主题切换（只在 mode=system 时有效）
if (typeof window !== 'undefined') {
  const mq = window.matchMedia('(prefers-color-scheme: dark)')
  mq.addEventListener('change', () => {
    if (useThemeStore.getState().mode === 'system') {
      const effective = getSystemPref()
      applyTheme(effective)
      useThemeStore.setState({ effective })
    }
  })
}
