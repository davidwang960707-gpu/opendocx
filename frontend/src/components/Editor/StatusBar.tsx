/** StatusBar — 编辑器底部状态条
 *
 * P0-B-6: 按设计稿 OCR 的 5 个指标
 *   字数 | 阅读时长 | 保存状态 | 关联 N 节点 | 引用 N 文档
 *
 * 数据源：
 *   - 字数 / 阅读时长：content 直接算（300 字/分钟）
 *   - 保存状态：父组件传入（unsaved | saving | saved | savedAt）
 *   - 关联节点 / 引用文档：预留真实知识图谱/引用关系入口，v0.1.0 不造假展示。
 */
import { useMemo } from 'react'

interface Props {
  content: string
  /** 是否有未保存改动 */
  dirty: boolean
  /** 保存中 */
  saving: boolean
  /** 刚保存成功，用于短暂反馈 */
  saveSuccess?: boolean
  /** 上次保存成功时间戳（ms） */
  lastSavedAt: number | null
}

interface Stats {
  wordCount: number
  readMinutes: number
  knowledgeNodes: number
  citedDocs: number
}

const READ_WPM = 300

export function computeStats(content: string): Stats {
  const wordCount = content.length
  const readMinutes = Math.max(1, Math.round(wordCount / READ_WPM))
  return {
    wordCount,
    readMinutes,
    knowledgeNodes: 0,
    citedDocs: 0,
  }
}

function formatSavedAgo(ts: number, now: number): string {
  const diff = Math.max(0, Math.floor((now - ts) / 1000))
  if (diff < 5) return '刚刚'
  if (diff < 60) return `${diff} 秒前`
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  return `${Math.floor(diff / 86400)} 天前`
}

export default function StatusBar({ content, dirty, saving, saveSuccess = false, lastSavedAt }: Props) {
  const stats = useMemo(() => computeStats(content), [content])
  const now = Date.now()

  let saveLabel: string
  let saveColor: string
  if (saving) {
    saveLabel = '保存中...'
    saveColor = '#FF9500'
  } else if (dirty) {
    saveLabel = '未保存'
    saveColor = '#FF9500'
  } else if (saveSuccess) {
    saveLabel = '刚刚保存'
    saveColor = '#34C759'
  } else if (lastSavedAt) {
    saveLabel = `已保存 ${formatSavedAgo(lastSavedAt, now)}`
    saveColor = '#34C759'
  } else {
    saveLabel = '未修改'
    saveColor = '#AEAEB2'
  }

  return (
    <footer className="status-bar" data-testid="status-bar">
      <span className="status-item">
        <span className="status-value">{stats.wordCount.toLocaleString()}</span>
        <span className="status-label">字数</span>
      </span>
      <span className="status-sep" />
      <span className="status-item">
        <span className="status-value">{stats.readMinutes}</span>
        <span className="status-label">阅读时长 分钟</span>
      </span>
      <span className="status-sep" />
      <span
        className={`status-item status-save-state${saving ? ' is-saving' : dirty ? ' is-dirty' : saveSuccess ? ' is-saved-flash' : ''}`}
        style={{ color: saveColor }}
      >
        <span className="status-value">{saveLabel}</span>
      </span>

      <span className="status-spacer" />

      {stats.knowledgeNodes > 0 && (
        <>
          <span className="status-item">
            <span className="status-value">{stats.knowledgeNodes}</span>
            <span className="status-label">关联 知识节点</span>
          </span>
          <span className="status-sep" />
        </>
      )}
      {stats.citedDocs > 0 && (
        <span className="status-item">
          <span className="status-value">{stats.citedDocs}</span>
          <span className="status-label">引用 文档</span>
        </span>
      )}
    </footer>
  )
}
