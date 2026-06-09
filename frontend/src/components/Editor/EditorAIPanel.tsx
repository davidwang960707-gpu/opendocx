/** EditorAIPanel — 编辑器右侧 AI 面板
 *
 * P0-B-4 + P1-UI-6: 真实文档分析 (调 /api/v1/editor/analyze)
 * - AI 状态头：节点 / 冲突 / 协作者
 * - AI Insight：术语一致性 / 接口一致性 / 知识关联 (来自后端规则分析)
 * - AI 摘要：置信度
 * - 健康度：分数 + 等级 (4 维拆解: heading/code/paragraph/link)
 * - AI 推荐：快捷动作
 * - 底部状态条
 *
 * 零 emoji，SVG 图标；纯 React + AntD + 全局 CSS 变量
 */
import { useEffect, useState } from 'react'
import { Avatar, Tooltip, Progress, Tag, Button } from 'antd'
import {
  RobotFilled, WarningFilled, LinkOutlined, ThunderboltFilled,
  CheckCircleFilled, FileTextOutlined, CodeOutlined, ClusterOutlined,
  BulbOutlined, ApiOutlined, PythonOutlined, LoadingOutlined,
  FireFilled, BookOutlined, DisconnectOutlined, AlertFilled,
} from '@ant-design/icons'
import { useAuthStore } from '../../stores/auth'
import { editorApi, type AnalyzeResponse } from '../../services/editorApi'
import { computeStats } from './StatusBar'

interface Props {
  content: string
  projectName?: string
  versionLabel?: string
  docTitle?: string
  versionId?: string
  docId?: string
  onInsertText?: (text: string) => void
  onAction?: (actionId: string) => void
}

// 协作者头像（mock，未来接协作服务）
const MOCK_COLLABORATORS = [
  { name: 'Admin', color: '#4F46E5' },
  { name: '李雷', color: '#0071e3' },
  { name: '韩梅梅', color: '#ff9f0a' },
]

export default function EditorAIPanel({
  content, projectName, versionLabel, docTitle, versionId, docId, onAction,
}: Props) {
  const { user } = useAuthStore()
  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult] = useState<AnalyzeResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const hasDocument = Boolean(docId && docTitle)

  // P1-UI-6: 调真接口 /api/v1/editor/analyze
  useEffect(() => {
    if (!hasDocument) {
      setResult(null)
      setError(null)
      setAnalyzing(false)
      return
    }
    if (!content || content.length < 50) {
      setResult(null)
      setError(null)
      setAnalyzing(false)
      return
    }
    let cancelled = false
    setAnalyzing(true)
    setError(null)
    // debounce 500ms — 避免输入太快频繁打后端
    const t = setTimeout(async () => {
      try {
        const r = await editorApi.analyze(content, versionId, docId)
        if (!cancelled) setResult(r)
      } catch (e: any) {
        if (!cancelled) setError(e?.message || '分析失败')
      } finally {
        if (!cancelled) setAnalyzing(false)
      }
    }, 500)
    return () => { cancelled = true; clearTimeout(t) }
  }, [content, versionId, docId, hasDocument])

  // 字数（实时）
  const wordCount = content.length
  const readMinutes = Math.max(1, Math.round(wordCount / 300))
  const s = computeStats(content)

  const health = result?.health ?? null
  const summary = result?.summary ?? null
  const term = result?.terminology
  const iface = result?.interface
  const related = result?.knowledge?.related ?? []

  const totalIssues = hasDocument ? (term?.issues.length ?? 0) + (iface?.issues.length ?? 0) : 0
  const linkedCount = hasDocument ? (related.length || s.knowledgeNodes) : 0

  const healthColor =
    !health ? '#AEAEB2' :
    health.score >= 85 ? '#34C759' :
    health.score >= 70 ? '#007AFF' : '#FF9500'

  return (
    <aside className="ai-panel">
      {/* 状态头 */}
      <header className="ai-panel-header">
        <div className="ai-state-line">
          <RobotFilled style={{ color: '#4F46E5', fontSize: 14 }} />
          <span className="ai-state-text">
            <strong>{linkedCount}</strong> 节点
          </span>
          <span className="ai-state-divider">·</span>
          <WarningFilled style={{ color: totalIssues > 0 ? '#FF9500' : '#34C759', fontSize: 13 }} />
          <span className="ai-state-text">
            <strong>{totalIssues}</strong> 冲突
          </span>
        </div>
        <div className="ai-collab-line">
          <Avatar.Group size="small" max={{ count: 3 }}>
            {MOCK_COLLABORATORS.map(c => (
              <Tooltip key={c.name} title={c.name}>
                <Avatar style={{ background: c.color, fontSize: 11 }}>{c.name[0]}</Avatar>
              </Tooltip>
            ))}
            <Tooltip title={user?.name || '你'}>
              <Avatar style={{ background: '#1D1D1F', fontSize: 11 }}>
                {(user?.name || '我')[0]}
              </Avatar>
            </Tooltip>
          </Avatar.Group>
        </div>
      </header>

      {/* AI Insight 卡 */}
      <section className="ai-card">
        <h3 className="ai-card-title">
          <BulbOutlined style={{ color: '#4F46E5' }} />
          AI Insight
        </h3>
        <div className="ai-insight-list">
          {/* 术语一致性 */}
          <InsightRow
            icon={<CheckCircleFilled style={{ color: term?.issues.length ? '#FF9500' : '#34C759' }} />}
            label="术语一致性"
            status={term?.issues.length
              ? `${term.issues.length} 处建议`
              : (term ? '通过' : '—')}
            chips={term?.issues}
            detailTags={term?.terms?.slice(0, 6).map(t => `${t.term} ×${t.count}`)}
            actionLabel="查看"
            onAction={() => onAction?.('lint-terminology')}
          />
          {/* 接口一致性 */}
          <InsightRow
            icon={<ApiOutlined style={{ color: iface?.issues.length ? '#FF9500' : '#34C759' }} />}
            label="接口一致性"
            status={iface
              ? (iface.issues.length ? `${iface.issues.length} 处建议` : `${iface.endpoints.length} 端点`)
              : '—'}
            chips={iface?.issues}
            detailTags={iface?.endpoints?.slice(0, 3).map(e => `${e.method} ${e.path}`)}
            actionLabel="查看"
            onAction={() => onAction?.('lint-interface')}
          />
          {/* 知识关联 */}
          <InsightRow
            icon={<ClusterOutlined style={{ color: '#007AFF' }} />}
            label="知识关联"
            status={related.length ? `${related.length} 个相关文档` : '—'}
            chips={related.slice(0, 4).map(r => r.title)}
            detailTags={related.slice(0, 3).map(r => `${r.match_count} 匹配`)}
            actionLabel="链接"
            onAction={() => onAction?.('link-knowledge')}
          />
        </div>
      </section>

      {/* AI 摘要 */}
      <section className="ai-card">
        <h3 className="ai-card-title">
          <FileTextOutlined style={{ color: '#4F46E5' }} />
          AI 摘要
          {summary && (
            <span className="ai-confidence">
              置信度 <strong>{summary.confidence}%</strong>
            </span>
          )}
        </h3>
        <p className="ai-summary-text">
          {!hasDocument
            ? '选择一篇文档后，AI 会在这里给出摘要、健康度和关联建议。'
            : summary?.text || '写够 50 字后 AI 会自动生成摘要...'}
        </p>
        {summary && health?.stats && (
          <div className="ai-summary-stats">
            <span><BookOutlined /> {health.stats.h1 + health.stats.h2 + health.stats.h3} 标题</span>
            <span><FireFilled /> {Math.round(health.stats.code_ratio * 100)}% 代码</span>
            <span><DisconnectOutlined /> {health.stats.links} 链接</span>
          </div>
        )}
      </section>

      {/* 健康度 */}
      <section className="ai-card">
        <h3 className="ai-card-title">
          <ThunderboltFilled style={{ color: healthColor }} />
          健康度
          {health && (
            <span className="ai-health-score" style={{ color: healthColor }}>
              <strong>{health.score}</strong> {health.grade}
            </span>
          )}
        </h3>
        <Progress
          percent={hasDocument ? (health?.score ?? 0) : 0}
          showInfo={false}
          strokeColor={healthColor}
          trailColor="#F5F5F7"
          strokeWidth={6}
        />
        {health?.breakdown && (
          <div className="ai-health-breakdown">
            <Bar label="标题" value={health.breakdown.heading} max={30} color="#007AFF" />
            <Bar label="代码" value={health.breakdown.code} max={20} color="#34C759" />
            <Bar label="段落" value={health.breakdown.paragraph} max={25} color="#FF9500" />
            <Bar label="链接" value={health.breakdown.link} max={25} color="#AF52DE" />
          </div>
        )}
        <div className="ai-health-hint">
          基于术语 / 接口 / 知识关联综合评估
        </div>
      </section>

      {/* AI 推荐 */}
      <section className="ai-card">
        <h3 className="ai-card-title">
          <CodeOutlined style={{ color: '#4F46E5' }} />
          AI 推荐
        </h3>
        <div className="ai-recommend-list">
          <Button
            block
            icon={<ApiOutlined />}
            onClick={() => onAction?.('generate-openapi')}
            className="ai-recommend-btn"
            disabled={!hasDocument || !iface || iface.endpoints.length === 0}
          >
            生成 OpenAPI 规范
            {iface && iface.endpoints.length > 0 && (
              <span className="ai-recommend-count">({iface.endpoints.length})</span>
            )}
          </Button>
          <Button
            block
            icon={<PythonOutlined />}
            onClick={() => onAction?.('generate-sdk')}
            className="ai-recommend-btn"
            disabled={!hasDocument || !iface || iface.endpoints.length === 0}
          >
            生成 Python SDK
          </Button>
        </div>
      </section>

      {/* 错误提示 */}
      {error && (
        <section className="ai-card ai-card-error">
          <AlertFilled style={{ color: '#FF3B30' }} />
          <span>{error}</span>
        </section>
      )}

      {/* 底部状态条 */}
      <footer className="ai-panel-footer">
        {!hasDocument ? (
          <span className="ai-footer-status">
            <span className="ai-dot idle" />
            请选择文档开始分析
          </span>
        ) : analyzing ? (
          <span className="ai-footer-status analyzing">
            <LoadingOutlined spin style={{ marginRight: 6 }} />
            AI 正在分析文档...
          </span>
        ) : (
          <span className="ai-footer-status">
            <span className="ai-dot" />
            AI 就绪 · 已分析 {wordCount} 字
          </span>
        )}
      </footer>
    </aside>
  )
}

function InsightRow({
  icon, label, status, chips, detailTags, actionLabel, onAction,
}: {
  icon: React.ReactNode
  label: string
  status: string
  chips?: string[]
  detailTags?: string[]
  actionLabel: string
  onAction: () => void
}) {
  return (
    <div className="ai-insight-row">
      <div className="ai-insight-row-top">
        {icon}
        <span className="ai-insight-label">{label}</span>
        <span className="ai-insight-status">{status}</span>
        <a className="ai-insight-action" onClick={onAction}>{actionLabel}</a>
      </div>
      {chips && chips.length > 0 && (
        <div className="ai-insight-chips">
          {chips.map((c, i) => <Tag key={i} className="ai-insight-chip">{c}</Tag>)}
        </div>
      )}
      {detailTags && detailTags.length > 0 && (
        <div className="ai-insight-detail">
          {detailTags.map((t, i) => <span key={i} className="ai-insight-tag">{t}</span>)}
        </div>
      )}
    </div>
  )
}

function Bar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100))
  return (
    <div className="ai-health-bar">
      <span className="ai-health-bar-label">{label}</span>
      <div className="ai-health-bar-track">
        <div
          className="ai-health-bar-fill"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="ai-health-bar-value">{value}</span>
    </div>
  )
}
