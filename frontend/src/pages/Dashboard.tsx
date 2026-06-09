/** Dashboard — P1-段1 W1 D-1 砍欢迎语 → "今天" 顶卡 (B 紧凑风)
 *
 * 1.0 (P0-R8): 欢迎回来 + 4 指标大块面 + 2 栏 (项目 + 活动)
 * 2.0 (P1-段1 D-1): "今天" 顶卡 (日期 + 4 紧凑数据点) + 4 趋势指标 Tile (含 7d sparkline)
 *   - 行高 40/32/24 (B 风 token)
 *   - 字号 24/20/16/14/12 (5 档严格)
 *   - 圆角 8/12/20 (3 档)
 *   - 阴影品牌色微光 (rgba(79,70,229,0.08))
 *   - 字体 Inter + HarmonyOS Sans SC
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Avatar, Button, Space } from 'antd'
import {
  FileTextOutlined, EditOutlined, RocketOutlined, PlusOutlined, ThunderboltFilled,
  ArrowRightOutlined, ClockCircleOutlined, EditFilled, TeamOutlined,
} from '@ant-design/icons'
import { projectApi, statsApi, documentApi, buildApi, type BuildManifestItem } from '../services/api'
import MainLayout from '../layouts/MainLayout'
import type { Project } from '../types/api'
import type { Document } from '../types/api'

interface Activity {
  id: string
  type: 'doc_create' | 'doc_update' | 'doc_publish' | 'build' | 'project_create'
  actor: string
  actorColor: string
  project: string
  projectId?: string
  target: string
  at: number
}

const MOCK_ACTORS = [
  { name: 'Admin', color: '#4F46E5' },
  { name: '李雷', color: '#0071e3' },
  { name: '韩梅梅', color: '#ff9f0a' },
  { name: 'Atlas', color: '#34C759' },
]

function pickActor(seed: number) {
  return MOCK_ACTORS[seed % MOCK_ACTORS.length]
}

function timeAgo(ts: number): string {
  const diff = Math.max(0, Math.floor((Date.now() - ts) / 1000))
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  return `${Math.floor(diff / 86400)} 天前`
}

const ACTIVITY_ICONS = {
  doc_create: <FileTextOutlined />,
  doc_update: <EditOutlined />,
  doc_publish: <RocketOutlined />,
  build: <RocketOutlined />,
  project_create: <PlusOutlined />,
}

const ACTIVITY_LABEL = {
  doc_create: '新建文档',
  doc_update: '更新文档',
  doc_publish: '发布文档',
  build: '触发构建',
  project_create: '新建项目',
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState<Project[]>([])
  const [manifest, setManifest] = useState<BuildManifestItem[]>([])
  const [activities, setActivities] = useState<Activity[]>([])
  // P1-段1 D-1: 4 紧凑数据点 + 7d trend (后端 /stats 扩)
  const [stats, setStats] = useState({
    project_count: 0,
    document_count: 0,
    published_count: 0,
    today_builds: 0,
    today_doc_updates: 0,
    pending_drafts: 0,
    online_editors: 0,
    trend_7d: { projects: [0, 0, 0, 0, 0, 0, 0], docs: [0, 0, 0, 0, 0, 0, 0], builds: [0, 0, 0, 0, 0, 0, 0] } as { projects: number[]; docs: number[]; builds: number[] },
  })

  useEffect(() => {
    // 项目列表
    projectApi.list().then((res) => {
      const list: Project[] = res.data?.data || []
      setProjects(list)
      // 用项目+构建历史生成 mock 活动
      const acts: Activity[] = []
      list.forEach((p, i) => {
        acts.push({
          id: `proj-${p.id}`,
          type: 'project_create',
          actor: pickActor(i).name,
          actorColor: pickActor(i).color,
          project: p.name,
          projectId: p.id,
          target: p.name,
          at: new Date(p.created_at).getTime(),
        })
      })
      // 拉 manifest 当作构建活动
      buildApi.manifest().then((r) => {
        const m: BuildManifestItem[] = r.data?.data || []
        setManifest(m)
        m.forEach((b, i) => {
          acts.push({
            id: `build-${b.build_id}`,
            type: 'build',
            actor: pickActor(i + 1).name,
            actorColor: pickActor(i + 1).color,
            project: b.project_name,
            projectId: b.project_id,
            target: `${b.project_name} · ${b.version}`,
            at: new Date(b.built_at).getTime(),
          })
        })
        acts.sort((a, b) => b.at - a.at)
        setActivities(acts.slice(0, 10))
      }).catch(() => {
        acts.sort((a, b) => b.at - a.at)
        setActivities(acts.slice(0, 10))
      })
    })
    // 拉文档总数 / 已发布
    statsApi.get().then((r) => setStats(r.data.data || {})).catch(() => {})
  }, [])

  const hero = projects[0]
  const rest = projects.slice(1)

  return (
    <MainLayout>
      {/* === R 后 §1: Hero 顶卡 (日期 + 欢迎 + 4 紧凑数据点, B 风紧凑 32px 行高) === */}
      <section
        data-testid="dashboard-today-card"
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          gap: 24, padding: '14px 20px', marginBottom: 32,
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          minHeight: 56,
          boxShadow: 'var(--shadow-hover)',
        }}
      >
        {/* 左: 日期 + 欢迎 */}
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, minWidth: 0 }}>
          <span style={{
            fontSize: 'var(--font-size-body)', fontWeight: 600, color: 'var(--text-primary)',
            whiteSpace: 'nowrap',
          }}>
            {new Intl.DateTimeFormat('zh-CN', { dateStyle: 'full' }).format(new Date())}
          </span>
          <span style={{ fontSize: 'var(--font-size-aux)', color: 'var(--text-tertiary)' }}>
            欢迎回来
          </span>
        </div>
        {/* 右: 4 紧凑数据点 (R 后: 24px gap, 留呼吸) */}
        <Space size={24} style={{ flexShrink: 0 }}>
          <TodayStat icon={<ThunderboltFilled />} label="今日构建" value={stats.today_builds} color="var(--brand-primary)" />
          <TodayStat icon={<EditFilled />} label="今日更新" value={stats.today_doc_updates} color="#0071e3" />
          <TodayStat icon={<TeamOutlined />} label="在线编辑" value={stats.online_editors} color="#34C759" />
        </Space>
      </section>

      {/* === R 后 §2: Metric strip — 4 段 divide-x 横幅 (替代 4 卡片) === */}
      <section
        data-testid="dashboard-metric-strip"
        style={{
          display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
          padding: '20px 0', marginBottom: 40,
          borderTop: '1px solid var(--border-subtle)',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <MetricStripCell label="项目总数" value={stats.project_count} accent="var(--brand-primary)" />
        <MetricStripCell label="文档总数" value={stats.document_count} accent="#0071e3" />
        <MetricStripCell label="已发布" value={stats.published_count} accent="#34C759" />
        <MetricStripCell label="今日构建" value={stats.today_builds} accent="#ff9f0a" isLast />
      </section>

      {/* === R 后 §3: 项目 + 活动 2 段 divide-y 列表 (无卡片, 留呼吸 32px 段间距) === */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)',
        gap: 48, marginBottom: 40,
      }}>
        {/* 左: 项目 (单栏 divide-y 列表, 禁卡片) */}
        <section>
          <SectionHeader
            title="项目"
            extra={
              <Button type="link" size="small" onClick={() => navigate('/projects')}>
                查看全部 <ArrowRightOutlined />
              </Button>
            }
          />
          {projects.length === 0 ? (
            <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 'var(--font-size-body)' }}>
              还没有项目，点击「查看全部」去新建
            </div>
          ) : (
            <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {projects.slice(0, 6).map((p, idx) => (
                <li
                  key={p.id}
                  onClick={() => navigate(`/projects/${p.id}/docs`)}
                  data-testid={`project-row-${p.slug}`}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 14,
                    padding: '14px 4px',
                    borderBottom: idx < Math.min(projects.length, 6) - 1 ? '1px solid var(--border-subtle)' : 'none',
                    cursor: 'pointer',
                    transition: 'background 0.15s',
                    borderRadius: 4,
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--bg-secondary)' }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
                >
                  <div style={{
                    width: 32, height: 32, borderRadius: 8,
                    background: p.brand_color || 'var(--brand-primary)',
                    color: '#FFF', fontWeight: 600, fontSize: 14,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0,
                  }}>{p.name[0]?.toUpperCase()}</div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: 'var(--font-size-body)', fontWeight: 600,
                      color: 'var(--text-primary)',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>{p.name}</div>
                    <div style={{
                      fontSize: 'var(--font-size-aux)', color: 'var(--text-tertiary)',
                      marginTop: 2,
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>{p.description || p.slug}</div>
                  </div>
                  <ArrowRightOutlined style={{ color: 'var(--text-tertiary)', fontSize: 12 }} />
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* 右: 最近活动 (单栏 divide-y 列表, 禁卡片) */}
        <section>
          <SectionHeader
            title="最近活动"
            extra={<ClockCircleOutlined style={{ color: 'var(--text-tertiary)' }} />}
          />
          {activities.length === 0 ? (
            <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 'var(--font-size-body)' }}>
              暂无活动
            </div>
          ) : (
            <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {activities.slice(0, 6).map((a, i) => (
                <li
                  key={a.id}
                  onClick={() => a.projectId && navigate(`/projects/${a.projectId}/docs`)}
                  data-testid={`activity-row-${a.id}`}
                  style={{
                    display: 'flex', alignItems: 'flex-start', gap: 12,
                    padding: '14px 4px',
                    borderBottom: i < Math.min(activities.length, 6) - 1 ? '1px solid var(--border-subtle)' : 'none',
                    cursor: a.projectId ? 'pointer' : 'default',
                  }}
                >
                  <Avatar size={28} style={{ background: a.actorColor, fontSize: 12, flexShrink: 0 }}>
                    {a.actor[0]}
                  </Avatar>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 'var(--font-size-body)', color: 'var(--text-primary)', lineHeight: 1.5 }}>
                      <strong style={{ fontWeight: 600 }}>{a.actor}</strong>{' '}
                      <span style={{ color: 'var(--text-secondary)' }}>{ACTIVITY_LABEL[a.type]}</span>{' '}
                      <span style={{ color: 'var(--brand-primary)' }}>{a.target}</span>
                    </div>
                    <div style={{
                      fontSize: 'var(--font-size-aux)', color: 'var(--text-tertiary)',
                      marginTop: 4, display: 'flex', alignItems: 'center', gap: 6,
                    }}>
                      <span>{a.project}</span>
                      <span>·</span>
                      <span>{timeAgo(a.at)}</span>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* === R 后 §4: 最近发布站点 (3 列, 复用 Published 同套卡片规格) === */}
      {manifest.length > 0 && (
        <>
          <SectionHeader
            title="最近发布站点"
            extra={
              <Button type="link" size="small" onClick={() => navigate('/published')}>
                查看全部 <ArrowRightOutlined />
              </Button>
            }
          />
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 32,
          }}>
            {manifest.slice(0, 3).map((b) => (
              <article
                key={b.build_id}
                data-testid={`site-thumbnail-${b.project_slug}-${b.version}`}
                onClick={() => window.open(b.url, '_blank', 'noopener')}
                style={{
                  cursor: 'pointer',
                  border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-elevated)', overflow: 'hidden',
                  boxShadow: 'var(--shadow-hover)',
                  transition: 'transform 0.15s, box-shadow 0.15s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 8px 24px rgba(123, 97, 255, 0.18)' }}
                onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = 'var(--shadow-hover)' }}
              >
                <div style={{ height: 4, background: b.brand_color || 'var(--brand-primary)' }} />
                <div style={{
                  background: 'var(--bg-soft)', padding: 16, height: 140,
                  display: 'flex', flexDirection: 'column', gap: 6,
                }}>
                  <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#FF5F57' }} />
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#FEBC2E' }} />
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#28C840' }} />
                  </div>
                  <div style={{ height: 6, background: b.brand_color || 'var(--brand-primary)', borderRadius: 2, width: '60%' }} />
                  <div style={{ height: 4, background: 'var(--border-subtle)', borderRadius: 2, width: '100%' }} />
                  <div style={{ height: 4, background: 'var(--border-subtle)', borderRadius: 2, width: '90%' }} />
                  <div style={{ height: 4, background: 'var(--border-subtle)', borderRadius: 2, width: '70%' }} />
                </div>
                <div style={{ padding: '14px 16px' }}>
                  <div style={{
                    fontSize: 'var(--font-size-body)', fontWeight: 600,
                    color: 'var(--text-primary)',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>{b.project_name}</div>
                  <div style={{
                    fontSize: 'var(--font-size-aux)', color: 'var(--text-tertiary)',
                    marginTop: 2, display: 'flex', alignItems: 'center', gap: 4,
                  }}>
                    <RocketOutlined style={{ fontSize: 10 }} />
                    <span>{b.version}</span>
                    <span>·</span>
                    <span style={{ fontVariantNumeric: 'tabular-nums' }}>{new Date(b.built_at).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </>
      )}
      {/* V2-A: 删除 "AI 助手 Atlas" 浮卡 (Admin反馈 "Atlas 也没有意义") */}
    </MainLayout>
  )
}

// === P1-段1 D-1: "今天" 顶卡单数据点 (B 风 12px 字号, 32px 行高, 紧凑 icon + label + 数字) ===
function TodayStat({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: number; color: string }) {
  return (
    <span
      data-testid={`today-stat-${label}`}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        height: 'var(--line-height-card)',  /* 32px */
        fontSize: 'var(--font-size-aux)',    /* 12px */
        color: 'var(--text-secondary)',
        fontVariantNumeric: 'tabular-nums',
      }}
    >
      <span style={{ color, display: 'inline-flex', alignItems: 'center' }}>{icon}</span>
      <span style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: 'var(--font-size-body)' }}>{value}</span>
      <span>{label}</span>
    </span>
  )
}

// === R 后 §2: Metric strip cell — 4 段 divide-x 横幅的单元 (无卡) ===
function MetricStripCell({ label, value, accent, isLast }: { label: string; value: number; accent: string; isLast?: boolean }) {
  return (
    <div
      data-testid={`strip-cell-${label}`}
      style={{
        display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 6,
        padding: '0 24px',
        borderRight: isLast ? 'none' : '1px solid var(--border-subtle)',
        minHeight: 56,
        justifyContent: 'center',
      }}
    >
      <div style={{ fontSize: 'var(--font-size-aux)', color: 'var(--text-tertiary)' }}>{label}</div>
      <div style={{
        fontSize: 'var(--font-size-section)',  /* 20px */
        fontWeight: 700, lineHeight: 1.1, color: 'var(--text-primary)',
        fontVariantNumeric: 'tabular-nums', letterSpacing: '-0.01em',
      }}>{value.toLocaleString()}</div>
    </div>
  )
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-secondary)' }}>
      <span style={{ color: 'var(--text-tertiary)' }}>{icon}</span>
      <span style={{ color: 'var(--text-primary)', fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>{value}</span>
      <span>{label}</span>
    </span>
  )
}

function SectionHeader({ title, extra }: { title: string; extra?: React.ReactNode }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      marginBottom: 14,
    }}>
      <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>{title}</h2>
      {extra}
    </div>
  )
}

// V2-A: 删除 KbdButton 组件 (快捷键入口改到 docs/USER-GUIDE.md 文档化, UI 不画)
