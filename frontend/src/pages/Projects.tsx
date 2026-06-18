/** Projects — P1-UI-2 重做
 *
 * 设计：项目卡网格（大卡 280px+，hover 浮起）+ 右侧状态矩阵
 * 状态矩阵：项目按状态（活跃/已暂停/草稿）+ 团队分组
 * 顶部：标题 + "新建项目" CTA + 搜索框
 *
 * 数据：复用 /api/v1/projects；status 字段在数据里没就展示 "活跃"
 * 描述里带可解析的标签做演示分组（demo 数据用）
 */
import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Drawer, Form, Input, message, Space, Input as AntInput, Tag, Tooltip, Select, Segmented, Tabs, Collapse, Popconfirm } from 'antd'
import {
  InboxOutlined, PlusOutlined, SearchOutlined, ProjectOutlined, BookOutlined,
  RocketOutlined, ClockCircleOutlined, TeamOutlined, CheckCircleFilled,
  EditOutlined, DeleteOutlined, InfoCircleOutlined, CopyOutlined, LinkOutlined, CodeOutlined,
  AppstoreOutlined, UnorderedListOutlined,
} from '@ant-design/icons'
import MarkdownUploader from '../components/Editor/MarkdownUploader'
import MainLayout from '../layouts/MainLayout'
import { useAuthStore } from '../stores/auth'
import { projectApi, versionApi, documentApi } from '../services/api'
import { PROJECT_TEMPLATES, getTemplate, type TemplateKind } from '../data/templates'
import type { Project, ProjectCreateRequest } from '../types/api'

const STATUS_META = {
  active: { label: '活跃', color: '#34C759', icon: <CheckCircleFilled /> },
  paused: { label: '已暂停', color: '#FF9500', icon: <ClockCircleOutlined /> },
  draft: { label: '草稿', color: '#AEAEB2', icon: <EditOutlined /> },
} as const

type Status = keyof typeof STATUS_META

function deriveStatus(p: Project): Status {
  if (p.status) return p.status as Status
  return 'active'
}

// === V2-B §1: Status strip cell (状态矩阵横幅单元, 同 Dashboard MetricStripCell) ===
function StatusStripCell({ label, value, accent, isLast }: { label: string; value: number; accent: string; isLast?: boolean }) {
  return (
    <div
      data-testid={`status-strip-${label}`}
      style={{
        display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 6,
        padding: '0 24px',
        borderRight: isLast ? 'none' : '1px solid var(--border-subtle)',
        minHeight: 48, justifyContent: 'center',
      }}
    >
      <div style={{ fontSize: 'var(--font-size-aux)', color: 'var(--text-tertiary)' }}>{label}</div>
      <div style={{
        fontSize: 20, fontWeight: 700, lineHeight: 1.1, color: accent,
        fontVariantNumeric: 'tabular-nums', letterSpacing: '-0.01em',
      }}>{value.toLocaleString()}</div>
    </div>
  )
}

export default function Projects() {
  const navigate = useNavigate()
  const currentUser = useAuthStore((s) => s.user)
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editProject, setEditProject] = useState<Project | null>(null)
  const [search, setSearch] = useState('')
  // P1-W2-P1: 视图模式 (grid 网格 / list 列表) - 默认 grid 保留 1.0 兼容
  const [viewMode, setViewMode] = useState<'grid' | 'list'>(() => (localStorage.getItem('projects.viewMode') as 'grid' | 'list') || 'grid')
  // P1-W2-P3: 顶部 Tab (我的项目 / 全部项目) - 默认 all
  const [scope, setScope] = useState<'mine' | 'all'>('all')
  // P1-W2-P3: 状态矩阵 4 段默认全部收折
  const [matrixOpen, setMatrixOpen] = useState<Record<Status, boolean>>({
    active: false, paused: false, draft: false,
  })
  // P1-W2-P5: Drawer 模板选择 + 创建中 loading
  const [templateKind, setTemplateKind] = useState<TemplateKind>('blank')
  const [creating, setCreating] = useState(false)
  // 批量上传 — 选项目 + 选版本
  const [uploadProjectId, setUploadProjectId] = useState<string | null>(null)
  const [uploadVersion, setUploadVersion] = useState<{ id: string; label: string } | null>(null)
  const [versionsByProject, setVersionsByProject] = useState<Record<string, Array<{ id: string; label: string }>>>({})
  const [form] = Form.useForm()

  const loadProjects = async () => {
    setLoading(true)
    try {
      const res = await projectApi.list()
      setProjects(res.data.data || [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadProjects() }, [])

  // 加载项目列表后, 拉每个项目的版本 (用于批量上传选择)
  useEffect(() => {
    if (projects.length === 0) return
    let cancelled = false
    ;(async () => {
      const map: Record<string, Array<{ id: string; label: string }>> = {}
      await Promise.all(projects.map(async p => {
        try {
          const res = await versionApi.list(p.id)
          const vers = (res.data.data || []).map((v: any) => ({ id: v.id, label: v.version }))
          map[p.id] = vers
        } catch { /* ignore */ }
      }))
      if (!cancelled) setVersionsByProject(map)
    })()
    return () => { cancelled = true }
  }, [projects.length])

  const handleCreate = async (values: any) => {
    setCreating(true)
    try {
      let pid: string
      let versionId: string | undefined
      if (editProject) {
        // 编辑现有项目
        await projectApi.update(editProject.id, values)
        pid = editProject.id
        versionId = (editProject as any).default_version_id
        message.success('项目更新成功')
      } else {
        // 新建项目
        const res: any = await projectApi.create(values)
        // axios 包装: r.data.data = 项目对象
        const proj = res?.data?.data || res?.data || res
        pid = proj.id
        versionId = proj.default_version_id
        message.success(`项目创建成功 (${getTemplate(templateKind).name})`)

        // P1-W2-P5: 模板有 seed 文档 → 批量创
        const tpl = getTemplate(templateKind)
        if (tpl.seeds.length > 0 && versionId) {
          let ok = 0
          for (const seed of tpl.seeds) {
            try {
              await documentApi.create(versionId, {
                slug: seed.slug,
                title: seed.title,
                content: seed.content,
                status: 'draft',
              })
              ok++
            } catch {
              // 单条 seed 失败不阻塞项目创建
            }
          }
          if (ok > 0) {
            message.success(`已预置 ${ok} 篇 seed 文档`, 1.5)
          }
        }
      }
      setModalOpen(false)
      setEditProject(null)
      setTemplateKind('blank')
      form.resetFields()
      loadProjects()
    } catch (err: any) {
      message.error(err.response?.data?.error?.message || '操作失败')
    } finally {
      setCreating(false)
    }
  }

  // P1-W2-P2: inline 状态切换 (列表 + 网格) — 乐观更新 + 失败回滚
  const handleStatusChange = async (p: Project, newStatus: Status) => {
    const oldStatus = p.status
    if (newStatus === oldStatus) return
    // 乐观更新本地 state
    setProjects(prev => prev.map(x => x.id === p.id ? { ...x, status: newStatus } : x))
    try {
      await projectApi.update(p.id, { status: newStatus })
      message.success(`已切换为「${STATUS_META[newStatus].label}」`)
    } catch (err: any) {
      // 回滚
      setProjects(prev => prev.map(x => x.id === p.id ? { ...x, status: oldStatus } : x))
      message.error(err.response?.data?.error?.message || '状态更新失败')
    }
  }

  // P1-W2-P4: 复制 helper — 走 navigator.clipboard.writeText, 失败降级 textarea
  const handleCopy = async (text: string, label: string) => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text)
      } else {
        // Fallback: textarea
        const ta = document.createElement('textarea')
        ta.value = text
        ta.style.position = 'fixed'
        ta.style.opacity = '0'
        document.body.appendChild(ta)
        ta.select()
        document.execCommand('copy')
        document.body.removeChild(ta)
      }
      message.success(`已复制 ${label}`, 1.2)
    } catch {
      message.error('复制失败,请手动选择')
    }
  }

  // P1-W2-P4: 拼装项目对外链接 (3 件)
  const buildLinks = (p: Project) => {
    const origin = window.location.origin
    const ver = (p as any).default_version_id || 'v1.0'
    return {
      slug: p.slug,
      siteUrl: `${origin}/docs/${p.slug}/${ver}/`,
      apiUrl: `${origin}/api/v1/projects/${p.id}`,
    }
  }

  const handleDelete = async (id: string, name: string) => {
    // P1-W2-P5: 改 Modal.confirm → Popconfirm 嵌入, 不再弹模态
    try {
      await projectApi.delete(id)
      message.success(`已删除「${name}」`)
      loadProjects()
    } catch (err: any) {
      message.error(err.response?.data?.error?.message || '删除失败')
    }
  }

  const openProjectDocs = (projectId: string) => {
    navigate(`/projects/${projectId}/docs`)
  }

  const filtered = useMemo(() => {
    let list = projects
    // P1-W2-P3: 顶部 Tab scope 过滤 (我的项目 = created_by=currentUser.id)
    if (scope === 'mine' && currentUser?.id) {
      list = list.filter(p => p.created_by === currentUser.id)
    }
    if (search.trim()) {
      const q = search.toLowerCase()
      list = list.filter(p =>
        p.name.toLowerCase().includes(q) ||
        (p.description || '').toLowerCase().includes(q) ||
        p.slug.toLowerCase().includes(q)
      )
    }
    return list
  }, [projects, search, scope, currentUser?.id])

  // 状态矩阵：按 status 分组
  const matrix = useMemo(() => {
    const g: Record<Status, Project[]> = { active: [], paused: [], draft: [] }
    for (const p of filtered) g[deriveStatus(p)].push(p)
    return g
  }, [filtered])

  return (
    <MainLayout>
      {/* 顶部 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 32, gap: 16, flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 32, fontWeight: 700, letterSpacing: '-0.02em' }}>项目</h1>
          <p style={{ margin: '4px 0 0', color: 'var(--text-secondary)', fontSize: 14 }}>
            管理你团队的所有知识项目，共 {projects.length} 个
          </p>
        </div>
        <Space wrap>
          {/* P1-W2-P3: 顶部 Tab 我的项目/全部项目 */}
          <Tabs
            activeKey={scope}
            onChange={(k) => setScope(k as 'mine' | 'all')}
            size="small"
            data-testid="projects-scope-tabs"
            items={[
              { key: 'mine', label: `我的项目 (${projects.filter(p => p.created_by === currentUser?.id).length})` },
              { key: 'all', label: `全部项目 (${projects.length})` },
            ]}
          />
          <AntInput
            allowClear
            prefix={<SearchOutlined style={{ color: 'var(--text-tertiary)' }} />}
            placeholder="搜索项目..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: 240 }}
          />
          {/* P1-W2-P1: 列表/网格 Segmented 切换 */}
          <Segmented
            value={viewMode}
            onChange={(v) => {
              const m = v as 'grid' | 'list'
              setViewMode(m)
              localStorage.setItem('projects.viewMode', m)
            }}
            options={[
              { label: '网格', value: 'grid', icon: <AppstoreOutlined /> },
              { label: '列表', value: 'list', icon: <UnorderedListOutlined /> },
            ]}
            data-testid="projects-view-toggle"
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditProject(null); setTemplateKind('blank'); form.resetFields(); setModalOpen(true) }}>
            新建项目
          </Button>
          {/* 批量上传 — 选项目+版本 → MarkdownUploader */}
          <Select
            placeholder="选择项目"
            value={uploadProjectId || undefined}
            onChange={(pid) => {
              setUploadProjectId(pid)
              const vs = versionsByProject[pid] || []
              const first = vs[0]
              setUploadVersion(first || null)
            }}
            style={{ width: 200 }}
            options={projects.map(p => ({ value: p.id, label: p.name }))}
            allowClear
            onClear={() => { setUploadProjectId(null); setUploadVersion(null) }}
          />
          {uploadProjectId && (
            <Select
              placeholder="选择版本"
              value={uploadVersion?.id}
              onChange={(vid) => {
                const v = (versionsByProject[uploadProjectId] || []).find(x => x.id === vid)
                setUploadVersion(v || null)
              }}
              style={{ width: 120 }}
              options={(versionsByProject[uploadProjectId] || []).map(v => ({ value: v.id, label: v.label }))}
            />
          )}
          {uploadVersion && (
            <MarkdownUploader
              versionId={uploadVersion.id}
              onUploaded={loadProjects}
              trigger={
                <Button
                  type="default"
                  icon={<InboxOutlined />}
                  data-testid="projects-batch-upload-btn"
                >
                  批量上传 .md
                </Button>
              }
            />
          )}
        </Space>
      </div>

      {/* === V2-B §1: 状态矩阵横幅 (R 后: 4 段 divide-x 横幅, 替代 4 stat 块) === */}
      <section
        data-testid="projects-status-strip"
        style={{
          display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
          padding: '16px 0', marginBottom: 32,
          borderTop: '1px solid var(--border-subtle)',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <StatusStripCell label="项目总数" value={projects.length} accent="var(--brand-primary)" />
        <StatusStripCell label="活跃" value={matrix.active.length} accent="#34C759" />
        <StatusStripCell label="已暂停" value={matrix.paused.length} accent="#FF9500" />
        <StatusStripCell label="草稿" value={matrix.draft.length} accent="#AEAEB2" isLast />
      </section>

      {loading ? (
        <div style={{ color: 'var(--text-tertiary)', padding: 40, textAlign: 'center' }}>加载中...</div>
      ) : filtered.length === 0 ? (
        <div style={{
          padding: '60px 20px', textAlign: 'center',
          border: '1px dashed var(--border)', borderRadius: 12,
          color: 'var(--text-tertiary)',
        }}>
          <ProjectOutlined style={{ fontSize: 48, marginBottom: 12, opacity: 0.5 }} />
          <div style={{ fontSize: 15, marginBottom: 4 }}>{search ? '没找到匹配的项目' : '还没有项目'}</div>
          <div style={{ fontSize: 12 }}>{search ? '换个关键词试试' : '点击右上角"新建项目"开始'}</div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 320px', gap: 24 }}>
          {/* 左: P1-W2-P1 viewMode=grid 用 1.0 网格 / viewMode=list 用 2.0 紧凑列表行 (36px 行高 6 列) */}
          {viewMode === 'grid' ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }} data-testid="projects-grid-view">
            {filtered.map(p => {
              const status = deriveStatus(p)
              const meta = STATUS_META[status]
              return (
                <article
                  key={p.id}
                  className="project-card"
                  onClick={() => openProjectDocs(p.id)}
                  data-testid={`project-card-${p.slug}`}
                >
                  {/* 顶部 brand bar */}
                  <div className="project-card-bar" style={{ background: p.brand_color || '#4F46E5' }} />
                  <div className="project-card-body">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                      <div
                        className="project-card-mark"
                        style={{ background: p.brand_color || '#4F46E5' }}
                      >
                        {p.name[0]?.toUpperCase()}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div
                          role="button"
                          tabIndex={0}
                          data-testid={`project-title-${p.slug}`}
                          onClick={(e) => { e.stopPropagation(); openProjectDocs(p.id) }}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault()
                              e.stopPropagation()
                              openProjectDocs(p.id)
                            }
                          }}
                          style={{
                            display: 'inline-block',
                            maxWidth: '100%',
                            fontSize: 16,
                            fontWeight: 600,
                            color: 'var(--text-primary)',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            cursor: 'pointer',
                          }}
                        >
                          {p.name}
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{p.slug}</div>
                      </div>
                    </div>
                    <p style={{
                      fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5,
                      margin: '0 0 16px', height: 40, overflow: 'hidden',
                      display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
                    }}>
                      {p.description || '暂无描述'}
                    </p>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-tertiary)' }}>
                      <Space size={12}>
                        <span><BookOutlined /> 文档</span>
                        <span><RocketOutlined /> 构建</span>
                        <span><TeamOutlined /> 团队</span>
                      </Space>
                      <Tag color={meta.color} style={{ margin: 0, fontSize: 10, padding: '0 6px', border: 'none', background: `${meta.color}15`, color: meta.color }} onClick={(e) => e.stopPropagation()}>
                        {meta.icon} {meta.label}
                      </Tag>
                    </div>
                  </div>
                  <div className="project-card-actions">
                    {/* P1-W2-P4: 3 件复制 icon (slug / 站点 URL / API 链接) */}
                    {(() => {
                      const links = buildLinks(p)
                      return (
                        <>
                          <Tooltip title={`复制 slug: ${links.slug}`}>
                            <Button
                              type="text" size="small" icon={<CopyOutlined />}
                              onClick={(e) => { e.stopPropagation(); handleCopy(links.slug, 'slug') }}
                              data-testid={`project-copy-slug-${p.slug}`}
                            />
                          </Tooltip>
                          <Tooltip title={`复制站点 URL: ${links.siteUrl}`}>
                            <Button
                              type="text" size="small" icon={<LinkOutlined />}
                              onClick={(e) => { e.stopPropagation(); handleCopy(links.siteUrl, '站点 URL') }}
                              data-testid={`project-copy-site-${p.slug}`}
                            />
                          </Tooltip>
                          <Tooltip title={`复制 API 链接: ${links.apiUrl}`}>
                            <Button
                              type="text" size="small" icon={<CodeOutlined />}
                              onClick={(e) => { e.stopPropagation(); handleCopy(links.apiUrl, 'API 链接') }}
                              data-testid={`project-copy-api-${p.slug}`}
                            />
                          </Tooltip>
                        </>
                      )
                    })()}
                    <Tooltip title="项目总览">
                      <Button
                        type="text" size="small" icon={<InfoCircleOutlined />}
                        onClick={(e) => { e.stopPropagation(); navigate(`/projects/${p.id}/docs`) }}
                        data-testid={`project-overview-btn-${p.slug}`}
                      />
                    </Tooltip>
                    <Tooltip title="编辑">
                      <Button
                        type="text" size="small" icon={<EditOutlined />}
                        onClick={(e) => { e.stopPropagation(); setEditProject(p); form.setFieldsValue(p); setModalOpen(true) }}
                      />
                    </Tooltip>
                    <Tooltip title="删除">
                      <Popconfirm
                        title={`确认删除「${p.name}」?`}
                        description="删除后不可恢复"
                        okText="删除"
                        cancelText="取消"
                        okButtonProps={{ danger: true }}
                        onConfirm={(e) => { e?.stopPropagation?.(); handleDelete(p.id, p.name) }}
                        onCancel={(e) => e?.stopPropagation?.()}
                      >
                        <Button
                          type="text" size="small" danger icon={<DeleteOutlined />}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </Popconfirm>
                    </Tooltip>
                  </div>
                </article>
              )
            })}
            </div>
          ) : (
            /* ── P1-W2-P1: 2.0 列表视图 (B 风 36px 行高 + 12px 字号 + 6 列) ── */
            <div data-testid="projects-list-view" style={{
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-elevated)',
              overflow: 'hidden',
            }}>
              {/* 表头 */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: '2fr 1fr 0.8fr 0.6fr 1fr 0.6fr',
                gap: 12, alignItems: 'center',
                padding: '8px 16px',
                height: 'var(--line-height-list)' /* 40px */,
                background: 'var(--bg-secondary)',
                borderBottom: '1px solid var(--border-subtle)',
                fontSize: 'var(--font-size-aux)', /* 12px */
                fontWeight: 600,
                color: 'var(--text-tertiary)',
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
              }}>
                <div>名称</div>
                <div>slug</div>
                <div>状态</div>
                <div style={{ textAlign: 'right' }}>文档</div>
                <div>最后活跃</div>
                <div style={{ textAlign: 'right' }}>操作</div>
              </div>
              {/* 列表行 - 36px 行高 */}
              {filtered.map(p => {
                const status = deriveStatus(p)
                const meta = STATUS_META[status]
                return (
                  <div
                    key={p.id}
                    onClick={() => navigate(`/projects/${p.id}/docs`)}
                    data-testid={`project-list-row-${p.slug}`}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '2fr 1fr 0.8fr 0.6fr 1fr 0.6fr',
                      gap: 12, alignItems: 'center',
                      padding: '0 16px',
                      height: 'var(--line-height-card)' /* 32px, B 风紧凑 */,
                      borderBottom: '1px solid var(--border-subtle)',
                      cursor: 'pointer',
                      transition: 'background 0.15s',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--bg-hover)' }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
                  >
                    {/* 名称 + 品牌色圆点 */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                      <div style={{
                        width: 8, height: 8, borderRadius: '50%',
                        background: p.brand_color || '#4F46E5', flexShrink: 0,
                      }} />
                      <span style={{
                        fontSize: 'var(--font-size-body)', /* 14px */
                        fontWeight: 500,
                        color: 'var(--text-primary)',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }}>{p.name}</span>
                    </div>
                    {/* slug */}
                    <div style={{
                      fontSize: 'var(--font-size-aux)', /* 12px */
                      color: 'var(--text-tertiary)',
                      fontFamily: 'var(--font-mono)',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>{p.slug}</div>
                    {/* 状态 — P1-W2-P2 inline 编辑 (Click 阻止 row navigate) */}
                    <div onClick={(e) => e.stopPropagation()}>
                      <Select
                        size="small"
                        variant="borderless"
                        value={status}
                        onChange={(v) => handleStatusChange(p, v as Status)}
                        style={{ width: 96 }}
                        data-testid={`project-status-select-${p.slug}`}
                        options={[
                          { value: 'active', label: <span style={{ color: STATUS_META.active.color, fontSize: 11 }}><CheckCircleFilled /> 活跃</span> },
                          { value: 'paused', label: <span style={{ color: STATUS_META.paused.color, fontSize: 11 }}><ClockCircleOutlined /> 已暂停</span> },
                          { value: 'draft', label: <span style={{ color: STATUS_META.draft.color, fontSize: 11 }}><EditOutlined /> 草稿</span> },
                        ]}
                      />
                    </div>
                    {/* 文档数 */}
                    <div style={{
                      fontSize: 'var(--font-size-aux)',
                      color: 'var(--text-secondary)',
                      textAlign: 'right',
                      fontVariantNumeric: 'tabular-nums',
                    }}>{p.doc_count ?? '—'}</div>
                    {/* 最后活跃 */}
                    <div style={{
                      fontSize: 'var(--font-size-aux)',
                      color: 'var(--text-tertiary)',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {p.last_activity_at ? new Date(p.last_activity_at).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
                    </div>
                    {/* 操作 */}
                    <div style={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }} onClick={(e) => e.stopPropagation()}>
                      <Tooltip title="编辑">
                        <Button type="text" size="small" icon={<EditOutlined />}
                          onClick={() => { setEditProject(p); form.setFieldsValue(p); setModalOpen(true) }}
                        />
                      </Tooltip>
                      <Tooltip title="删除">
                        <Popconfirm
                          title={`确认删除「${p.name}」?`}
                          description="删除后不可恢复"
                          okText="删除"
                          cancelText="取消"
                          okButtonProps={{ danger: true }}
                          onConfirm={() => handleDelete(p.id, p.name)}
                        >
                          <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                        </Popconfirm>
                      </Tooltip>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* 右：状态矩阵 (P1-W2-P3: 4 段默认收折, 顶部 strip 仍常显) */}
          <aside style={{ position: 'sticky', top: 24, alignSelf: 'start' }}>
            <div style={{
              border: '1px solid var(--border-subtle)', borderRadius: 12,
              background: 'var(--bg-elevated)', overflow: 'hidden',
            }}>
              <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>状态矩阵</div>
                <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>点击展开各状态分组</div>
              </div>
              <Collapse
                ghost
                size="small"
                activeKey={(Object.keys(matrixOpen) as Status[]).filter(k => matrixOpen[k])}
                onChange={(keys) => {
                  const next = { ...matrixOpen }
                  ;(Object.keys(matrixOpen) as Status[]).forEach(k => { next[k] = (keys as string[]).includes(k) })
                  setMatrixOpen(next)
                }}
                data-testid="projects-matrix-collapse"
                items={(Object.keys(STATUS_META) as Status[]).map((s) => {
                  const meta = STATUS_META[s]
                  const list = matrix[s]
                  return {
                    key: s,
                    label: (
                      <Space size={6}>
                        <span style={{ color: meta.color, fontSize: 12 }}>{meta.icon}</span>
                        <span style={{ fontSize: 12, color: 'var(--text-primary)', fontWeight: 500 }}>{meta.label}</span>
                        <span style={{ fontSize: 11, color: 'var(--text-tertiary)', fontVariantNumeric: 'tabular-nums' }}>{list.length}</span>
                      </Space>
                    ),
                    children: list.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                        {list.slice(0, 6).map(p => (
                          <div
                            key={p.id}
                            onClick={() => navigate(`/projects/${p.id}/docs`)}
                            style={{
                              fontSize: 12, color: 'var(--text-secondary)', cursor: 'pointer',
                              padding: '2px 0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.color = 'var(--brand-primary)'}
                            onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-secondary)'}
                          >
                            {p.name}
                          </div>
                        ))}
                        {list.length > 6 && (
                          <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>还有 {list.length - 6} 个...</div>
                        )}
                      </div>
                    ) : (
                      <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>无</div>
                    ),
                  }
                })}
              />
            </div>
          </aside>
        </div>
      )}

      {/* P1-W2-P5: 新建/编辑项目 Drawer (替代 Modal) */}
      <Drawer
        title={editProject ? '编辑项目' : '新建项目'}
        open={modalOpen}
        onClose={() => { setModalOpen(false); setEditProject(null) }}
        width={520}
        footer={
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={() => { setModalOpen(false); setEditProject(null) }}>取消</Button>
            <Button type="primary" onClick={() => form.submit()} loading={creating}>
              {editProject ? '保存' : '创建'}
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          {!editProject && (
            <>
              {/* P1-W2-P5: 模板选择 — 3 卡片 */}
              <Form.Item label="项目模板" style={{ marginBottom: 16 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
                  {PROJECT_TEMPLATES.map(t => (
                    <div
                      key={t.kind}
                      onClick={() => {
                        setTemplateKind(t.kind)
                        // 自动填默认值 (用户可改)
                        form.setFieldsValue({
                          description: t.defaultDescription,
                          brand_color: t.defaultColor,
                        })
                      }}
                      style={{
                        padding: 12,
                        border: `1.5px solid ${templateKind === t.kind ? 'var(--brand-primary)' : 'var(--border-subtle)'}`,
                        borderRadius: 8,
                        cursor: 'pointer',
                        background: templateKind === t.kind ? 'var(--brand-primary-08, rgba(123,97,255,0.08))' : 'var(--bg-elevated)',
                        transition: 'all 0.15s',
                      }}
                      data-testid={`template-card-${t.kind}`}
                    >
                      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
                        {t.name}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-tertiary)', lineHeight: 1.4 }}>
                        {t.blurb}
                      </div>
                      {t.seeds.length > 0 && (
                        <div style={{ fontSize: 10, color: 'var(--brand-primary)', marginTop: 6 }}>
                          预置 {t.seeds.length} 篇文档
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </Form.Item>
            </>
          )}
          <Form.Item name="name" label="项目名称" rules={[{ required: true }]}>
            <Input placeholder="例: OpenDocX Demo" />
          </Form.Item>
          <Form.Item name="slug" label="项目标识" rules={[{ required: true }, { pattern: /^[a-z0-9-]+$/, message: '仅小写字母、数字、连字符' }]}>
            <Input placeholder="例: insight" disabled={!!editProject} />
          </Form.Item>
          <Form.Item name="description" label="项目描述">
            <Input.TextArea rows={3} placeholder="简要描述项目..." />
          </Form.Item>
          <Form.Item name="brand_color" label="品牌色" initialValue="#4F46E5">
            <Input type="color" style={{ width: 60, height: 32, padding: 2 }} />
          </Form.Item>
        </Form>
      </Drawer>
    </MainLayout>
  )
}
