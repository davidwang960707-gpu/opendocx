import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Empty, Input, message, Space, Spin, Tag, Typography } from 'antd'
import {
  ArrowRightOutlined,
  ClockCircleOutlined,
  CopyOutlined,
  FileTextOutlined,
  GlobalOutlined,
  LinkOutlined,
  ReloadOutlined,
  RocketOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import MainLayout from '../layouts/MainLayout'
import { buildApi, type BuildManifestItem } from '../services/api'
import '../styles/published.css'

const { Text } = Typography

export default function Published() {
  const navigate = useNavigate()
  const [items, setItems] = useState<BuildManifestItem[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const res = await buildApi.manifest()
      setItems(res.data.data || [])
    } catch (e) {
      message.error('加载已发布清单失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const stats = useMemo(() => {
    const totalDocs = items.reduce((sum, item) => sum + item.doc_count, 0)
    const projects = new Set(items.map(item => item.project_id)).size
    const latest = items
      .map(item => new Date(item.built_at).getTime())
      .filter(Number.isFinite)
      .sort((a, b) => b - a)[0]
    return {
      sites: items.length,
      projects,
      totalDocs,
      latestBuiltAt: latest ? fmtTime(new Date(latest).toISOString()) : '-',
    }
  }, [items])

  const sortedItems = useMemo(() => {
    const q = search.trim().toLowerCase()
    return items
      .filter(item => {
        if (!q) return true
        return item.project_name.toLowerCase().includes(q)
          || item.project_slug.toLowerCase().includes(q)
          || item.version.toLowerCase().includes(q)
      })
      .sort((a, b) => new Date(b.built_at).getTime() - new Date(a.built_at).getTime())
  }, [items, search])

  const copyUrl = (url: string) => {
    const fullUrl = `${window.location.origin}${url}`
    navigator.clipboard.writeText(fullUrl)
    message.success('已复制发布 URL')
  }

  return (
    <MainLayout subtitle="已发布站点" contentMaxWidth="full">
      <div className="page-toolbar">
        <div className="page-toolbar-left">
          <h1 className="page-title">
            <GlobalOutlined style={{ marginRight: 8 }} />
            已发布站点
          </h1>
          <Text type="secondary" style={{ fontSize: 12 }}>
            管理已构建的文档站点、复制 URL、检查最近构建状态
          </Text>
        </div>
        <div className="page-toolbar-right">
          <Space size={16}>
            <Input
              allowClear
              prefix={<SearchOutlined style={{ color: 'var(--text-tertiary)' }} />}
              placeholder="搜索项目、slug 或版本"
              value={search}
              onChange={event => setSearch(event.target.value)}
              style={{ width: 280 }}
            />
            <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          </Space>
        </div>
      </div>

      {loading ? (
        <div className="pub-loading">
          <Spin size="large" />
        </div>
      ) : items.length === 0 ? (
        <div className="pub-empty">
          <div className="pub-empty-icon">
            <RocketOutlined />
          </div>
          <div className="pub-empty-title">还没有发布的站点</div>
          <div className="pub-empty-desc">进入项目管理，发布文档并触发构建后会出现在这里。</div>
          <Button type="primary" onClick={() => navigate('/projects')}>前往项目管理</Button>
        </div>
      ) : (
        <div className="pub-page pub-page--admin">
          <section className="pub-admin-stats" data-testid="published-stats-strip">
            <StatCard label="已发布站点" value={stats.sites} />
            <StatCard label="项目" value={stats.projects} />
            <StatCard label="文档总数" value={stats.totalDocs} />
            <StatCard label="最近构建" value={stats.latestBuiltAt} compact />
          </section>

          {sortedItems.length === 0 ? (
            <div className="admin-table-shell">
              <Empty description="没有匹配的发布站点" style={{ padding: 60 }} />
            </div>
          ) : (
            <div className="pub-site-list">
              {sortedItems.map(item => (
                <SiteRow
                  key={`${item.project_id}-${item.version_id}`}
                  item={item}
                  onCopy={() => copyUrl(item.url)}
                  onOpen={() => window.open(item.url, '_blank', 'noopener')}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </MainLayout>
  )
}

function StatCard({ label, value, compact }: { label: string; value: string | number; compact?: boolean }) {
  return (
    <div className="pub-admin-stat">
      <Text type="secondary" className="pub-admin-stat-label">{label}</Text>
      <div className={compact ? 'pub-admin-stat-value pub-admin-stat-value--compact' : 'pub-admin-stat-value'}>
        {value}
      </div>
    </div>
  )
}

function SiteRow({
  item,
  onCopy,
  onOpen,
}: {
  item: BuildManifestItem
  onCopy: () => void
  onOpen: () => void
}) {
  return (
    <article className="pub-site-row" style={{ ['--brand-color' as any]: item.brand_color }}>
      <div className="pub-site-accent" />
      <div className="pub-site-main">
        <div className="pub-site-title-row">
          <div>
            <div className="pub-site-title">{item.project_name}</div>
            <div className="pub-site-url">/{item.project_slug}</div>
          </div>
          <Tag className="pub-site-version">{item.version}</Tag>
        </div>
        <div className="pub-site-meta">
          <span><FileTextOutlined /> {item.doc_count} 篇</span>
          <span><ClockCircleOutlined /> {item.duration ?? 0}s 构建</span>
          <span><ClockCircleOutlined /> {fmtTime(item.built_at)}</span>
          <span><LinkOutlined /> {item.url}</span>
        </div>
      </div>
      <div className="pub-site-actions">
        <Button icon={<CopyOutlined />} onClick={onCopy}>复制 URL</Button>
        <Button type="primary" icon={<ArrowRightOutlined />} onClick={onOpen}>打开站点</Button>
      </div>
    </article>
  )
}

function fmtTime(iso: string) {
  const date = new Date(iso)
  const diffMs = Date.now() - date.getTime()
  const mins = Math.floor(diffMs / 60000)
  if (mins < 1) return '刚刚'
  if (mins < 60) return `${mins} 分钟前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days} 天前`
  return date.toLocaleString('zh-CN', { hour12: false }).substring(0, 10)
}
