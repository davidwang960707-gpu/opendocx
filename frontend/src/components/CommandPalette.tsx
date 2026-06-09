/** CommandPalette — ⌘K 全局命令面板
 *
 * P0-B-8: 全局快捷键 ⌘K / Ctrl+K 唤出，模糊搜索命令列表
 * P1-W1-D-4: query ≥ 2 字时并行调 /api/v1/search 拉文档结果
 * 命令分两类：
 *   - 静态（导航/操作）：所有页面可用
 *   - 动态（上下文相关）：当前页面注册
 *   - 文档（/search 端点，embedding 语义搜索）
 *
 * 键盘交互：
 *   - ↑↓ 选中 / Enter 执行 / Esc 关闭
 *   - 输入过滤（大小写不敏感，子串匹配 label + keyword + group）
 *   - 文档结果可点跳转 /projects/{slug}/docs?doc={id}
 */
import { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { Modal, Input, Spin, Empty } from 'antd'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import {
  DashboardOutlined, ProjectOutlined, FileTextOutlined, RocketOutlined,
  PlusOutlined, SaveOutlined, EditOutlined, CompressOutlined, SyncOutlined,
  LogoutOutlined, GlobalOutlined, ThunderboltOutlined, EyeOutlined,
  ArrowLeftOutlined, ReloadOutlined, SearchOutlined,
} from '@ant-design/icons'

interface DocResult {
  document_id: string
  title: string
  content_snippet: string
  score: number
  project_slug: string
  version: string
}

export interface Command {
  id: string
  label: string
  group: '导航' | '项目' | '文档' | 'AI' | '操作' | '搜索结果'
  keywords?: string[]
  shortcut?: string
  icon?: React.ReactNode
  /** 当 visible = false 也显示在面板（用于 AI 之类需选区） */
  requiresSelection?: boolean
  /** 文档结果类型，run 跳路由 */
  doc?: DocResult
  run: () => void | Promise<void>
}

interface Props {
  open: boolean
  onClose: () => void
  commands: Command[]
}

const FUZZY_HIGHLIGHT = (text: string, q: string) => {
  if (!q) return text
  const idx = text.toLowerCase().indexOf(q.toLowerCase())
  if (idx < 0) return text
  return (
    <>
      {text.slice(0, idx)}
      <mark style={{ background: '#FFF4E5', color: '#874D00', padding: 0 }}>{text.slice(idx, idx + q.length)}</mark>
      {text.slice(idx + q.length)}
    </>
  )
}

export default function CommandPalette({ open, onClose, commands }: Props) {
  const [query, setQuery] = useState('')
  const [activeIdx, setActiveIdx] = useState(0)
  const [docResults, setDocResults] = useState<DocResult[]>([])
  const [searching, setSearching] = useState(false)
  const inputRef = useRef<any>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const navigate = useNavigate()

  // P1-W1-D-4: query ≥ 2 字时调 /api/v1/search (embedding 语义搜索)，debounce 200ms
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    const q = query.trim()
    if (q.length < 2) {
      setDocResults([])
      setSearching(false)
      return
    }
    setSearching(true)
    debounceRef.current = setTimeout(async () => {
      try {
        // P1-W1-D-4: 用 axios 直调 + 手动加 JWT header (services/api 不导出 api 实例)
        const token = localStorage.getItem('token')
        const resp = await axios.post<DocResult[] | { data: DocResult[] }>(
          '/api/v1/search',
          { query: q, limit: 5 },
          { timeout: 8000, headers: token ? { Authorization: `Bearer ${token}` } : {} },
        )
        const body: any = resp.data
        const data: DocResult[] = Array.isArray(body) ? body : (body?.data || [])
        setDocResults(data)
      } catch (err) {
        // 搜索失败不打断命令面板
        console.warn('[CommandPalette] /search 失败:', err)
        setDocResults([])
      } finally {
        setSearching(false)
      }
    }, 200)
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [query])

  // 过滤 + 文档结果合并
  const filtered = useMemo(() => {
    const q = query.trim()
    const cmdFiltered = !q ? commands : commands.filter(c => {
      const hay = (c.label + ' ' + c.group + ' ' + (c.keywords?.join(' ') || '')).toLowerCase()
      return hay.includes(q.toLowerCase())
    })
    // 文档结果统一封装为 Command (group='搜索结果')
    const docCmds: Command[] = docResults.map(d => ({
      id: `doc:${d.document_id}`,
      label: d.title,
      group: '搜索结果',
      keywords: [d.content_snippet.slice(0, 40)],
      icon: <FileTextOutlined />,
      doc: d,
      run: () => {
        navigate(`/projects/${d.project_slug}/docs?doc=${d.document_id}&v=${d.version}`)
      },
    }))
    return [...cmdFiltered, ...docCmds]
  }, [commands, query, docResults, navigate])

  // 重置 activeIdx 当 query 变化
  useEffect(() => { setActiveIdx(0) }, [query, open])

  // 打开时聚焦输入框
  useEffect(() => {
    if (open) {
      setQuery('')
      setActiveIdx(0)
      // 下一帧 focus
      setTimeout(() => inputRef.current?.focus(), 0)
    }
  }, [open])

  // 滚动 active 项到视口
  useEffect(() => {
    if (!listRef.current) return
    const el = listRef.current.querySelector(`[data-cmd-idx="${activeIdx}"]`)
    if (el) el.scrollIntoView({ block: 'nearest' })
  }, [activeIdx])

  const runCommand = useCallback(async (cmd: Command) => {
    onClose()
    // 等关闭动画再 run，避免 modal 抢占焦点
    setTimeout(() => { cmd.run() }, 50)
  }, [onClose])

  // 键盘
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIdx(i => Math.min(filtered.length - 1, i + 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIdx(i => Math.max(0, i - 1))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      const cmd = filtered[activeIdx]
      if (cmd) runCommand(cmd)
    }
  }

  // 按 group 分组
  const grouped = useMemo(() => {
    const g: Record<string, Command[]> = {}
    for (const c of filtered) {
      (g[c.group] = g[c.group] || []).push(c)
    }
    return g
  }, [filtered])

  let runningIdx = -1

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      closable={false}
      width={640}
      styles={{
        body: { padding: 0 },
        content: { padding: 0, borderRadius: 12, overflow: 'hidden' },
      }}
      maskClosable
      destroyOnHidden
    >
      <div className="cmd-palette">
        <div className="cmd-input-row">
          <Input
            ref={inputRef}
            size="large"
            placeholder="输入命令或搜索...（↑↓ 选择，Enter 执行，Esc 关闭）"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            bordered={false}
            prefix={<span style={{ color: '#AEAEB2', fontSize: 14 }}>⌘K</span>}
            style={{ fontSize: 15, padding: '14px 0' }}
          />
        </div>
        <div className="cmd-list" ref={listRef} data-testid="cmd-list">
          {searching && (
            <div className="cmd-searching" data-testid="cmd-searching">
              <Spin size="small" /> <span style={{ marginLeft: 8, color: '#86868B', fontSize: 13 }}>正在搜索文档...</span>
            </div>
          )}
          {filtered.length === 0 ? (
            <div className="cmd-empty">
              没有匹配的命令。试试「项目」「文档」「保存」。
            </div>
          ) : (
            Object.entries(grouped).map(([group, cmds]) => (
              <div key={group} className="cmd-group">
                <div className="cmd-group-title">{group}</div>
                {cmds.map((c) => {
                  runningIdx++
                  const isActive = runningIdx === activeIdx
                  return (
                    <div
                      key={c.id}
                      data-cmd-idx={runningIdx}
                      className={`cmd-item ${isActive ? 'active' : ''}`}
                      onMouseEnter={() => setActiveIdx(filtered.indexOf(c))}
                      onClick={() => runCommand(c)}
                    >
                      <span className="cmd-icon">{c.icon}</span>
                      <span className="cmd-label">{FUZZY_HIGHLIGHT(c.label, query)}</span>
                      {c.keywords && c.keywords.length > 0 && (
                        <span className="cmd-keywords">
                          {c.keywords.slice(0, 3).map(k => (
                            <span key={k} className="cmd-keyword">{k}</span>
                          ))}
                        </span>
                      )}
                      {c.shortcut && (
                        <span className="cmd-shortcut">{c.shortcut}</span>
                      )}
                    </div>
                  )
                })}
              </div>
            ))
          )}
        </div>
        <div className="cmd-footer">
          <span><kbd>↑</kbd><kbd>↓</kbd> 选择</span>
          <span><kbd>↵</kbd> 执行</span>
          <span><kbd>esc</kbd> 关闭</span>
          <span style={{ marginLeft: 'auto', color: '#AEAEB2' }}>
            {filtered.length} 个 · {docResults.length > 0 && <><SearchOutlined /> {docResults.length} 文档</>}
          </span>
        </div>
      </div>
    </Modal>
  )
}
