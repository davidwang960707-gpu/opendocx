/** i18n 工具 — 轻量自建, 不引入 react-i18next
 *
 * 用法:
 *   import { t, setLocale, getLocale, LocaleProvider } from '../i18n'
 *   <LocaleProvider>
 *     <App />
 *   </LocaleProvider>
 *   t('nav.dashboard')  // → "概览" or "Dashboard"
 *
 * 数据源: ./zh.json + ./en.json (扁平键, 点分访问)
 * 持久化: localStorage key = 'opendocx-locale' (默认 'zh-CN')
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import zh from './zh.json'
import en from './en.json'

export type Locale = 'zh-CN' | 'en-US'

const TRANSLATIONS: Record<Locale, any> = {
  'zh-CN': zh,
  'en-US': en,
}

const STORAGE_KEY = 'opendocx-locale'

function detectInitialLocale(): Locale {
  if (typeof window === 'undefined') return 'zh-CN'
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'zh-CN' || stored === 'en-US') return stored
  const browser = navigator.language || 'zh-CN'
  return browser.startsWith('zh') ? 'zh-CN' : 'en-US'
}

/** 扁平键访问: t('nav.dashboard') → TRANSLATIONS[locale].nav.dashboard */
export function t(key: string, locale?: Locale, vars?: Record<string, string | number>): string {
  const l = locale || (typeof window !== 'undefined' ? (localStorage.getItem(STORAGE_KEY) as Locale) : null) || 'zh-CN'
  const dict = TRANSLATIONS[l] || TRANSLATIONS['zh-CN']
  const parts = key.split('.')
  let v: any = dict
  for (const p of parts) {
    v = v?.[p]
    if (v === undefined) return key
  }
  if (typeof v !== 'string') return key
  if (!vars) return v
  return v.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? `{${k}}`))
}

interface LocaleCtx {
  locale: Locale
  setLocale: (l: Locale) => void
  t: (key: string, vars?: Record<string, string | number>) => string
}

const Ctx = createContext<LocaleCtx>({
  locale: 'zh-CN',
  setLocale: () => {},
  t: (k) => k,
})

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(detectInitialLocale)

  useEffect(() => {
    document.documentElement.setAttribute('lang', locale)
    localStorage.setItem(STORAGE_KEY, locale)
  }, [locale])

  const setLocale = useCallback((l: Locale) => setLocaleState(l), [])
  const tFn = useCallback(
    (key: string, vars?: Record<string, string | number>) => t(key, locale, vars),
    [locale],
  )

  return <Ctx.Provider value={{ locale, setLocale, t: tFn }}>{children}</Ctx.Provider>
}

export function useLocale() {
  return useContext(Ctx)
}

export function getLocale(): Locale {
  return (typeof window !== 'undefined' ? (localStorage.getItem(STORAGE_KEY) as Locale) : null) || 'zh-CN'
}
