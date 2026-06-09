/**
 * ProjectOverview — 项目总览内容组件
 *
 * 路由 (历史): /projects/:projectId (R13 起重定向到 /docs)
 * 现在用法 (R13):
 *   - Documents.tsx 没选 doc/folder 时, 在 docs-main-body 里渲染 <ProjectOverview embedded ... />
 *   - 保留独立 page wrapper 兼容老链接重定向
 *
 * 设计 (Admin R13 决策):
 *   - embedded=true (默认 false):
 *     - 删顶部"← 返回项目列表" + 面包屑 (docs-main-header 已有)
 *     - 删品牌色 banner + 里面的"进入文档树"按钮
 *     - 5 卡 → 4 卡 (删 "文件夹数", 留 文档/已发布/版本/构建)
 *     - grid minmax(180px, 1fr) 适配 720px 主区宽
 *     - 保留 文档结构概览 (8 个 root 节点) + 版本列表
 *   - 接受 externalProject/externalVersions/externalBuilds/externalDocTree (R13 防重复 fetch)
 *
 * 老的 5 卡包括文件夹数, 是因为 overview 当独立页时用户能 1 屏看 5 个数字;
 * 现在嵌进 docs 720px 主区, 装 5 张 180px 卡片要折 2 行, 删 1 张 (重要性最低的 文件夹数)
 */
import { useEffect, useState, useMemo } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  Typography, Button, Space, Spin, Tag, Tooltip, Empty, Breadcrumb,
} from 'antd'
import {
  FileTextOutlined, CheckCircleOutlined, FolderOutlined,
  RocketOutlined, ClockCircleOutlined, ProjectOutlined,
  HistoryOutlined, ArrowRightOutlined, HomeOutlined, EditOutlined,
} from '@ant-design/icons'
import { projectApi, versionApi, documentApi, buildApi } from '../services/api'
import MainLayout from '../layouts/MainLayout'
import ProjectContextPanel from '../components/ProjectContextPanel'
import IndexDocEditor, { type IndexDoc } from '../components/IndexDocEditor'
import { formatDistanceToNow } from '../utils/time'

const { Text, Title } = Typography

interface ProjectDetail {
  id: string
  name: string
  slug: string
  description: string
  brand_color: string
  status: string
  created_at: string
  updated_at: string
}

export interface DocumentTreeNode {
  id: string
  title: string
  status: 'draft' | 'published' | 'archived'
  is_folder?: boolean
  children?: DocumentTreeNode[]
}

interface StatCard {
  label: string
  value: number | string
  icon: React.ReactNode
  color: string
  tip?: string
}

interface ProjectOverviewProps {
  /** Admin R13: embedded 模式 — 在 /docs 没选状态时嵌进 docs-main-body */
  embedded?: boolean
  /** Admin R13: 接受外部传入数据, 避免 embedded 时重复 fetch (Documents.tsx 自己已 fetch) */
  externalProject?: ProjectDetail | null
  externalVersions?: any[]
  externalDocTree?: DocumentTreeNode[]
  externalBuilds?: any[]
  /** Admin R13: embedded 时点击文档结构卡 → 选 doc/folder (由 Documents 接管) */
  onSelectDoc?: (docId: string) => void
}

export default function ProjectOverview({
  embedded = false,
  externalProject,
  externalVersions,
  externalDocTree,
  externalBuilds,
  onSelectDoc,
}: ProjectOverviewProps) {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  // Admin R13: 优先用 external, 否则自己 fetch (独立访问 / 老链接重定向的场景)
  const [project, setProject] = useState<ProjectDetail | null>(externalProject ?? null)
  const [versions, setVersions] = useState<any[]>(externalVersions ?? [])
  const [docTree, setDocTree] = useState<DocumentTreeNode[]>(externalDocTree ?? [])
  const [builds, setBuilds] = useState<any[]>(externalBuilds ?? [])
  const [loading, setLoading] = useState(!embedded)
  const [error, setError] = useState<string | null>(null)
  // 段 C 收官: 首页配置 (slug=index doc) 编辑器
  const [indexDoc, setIndexDoc] = useState<IndexDoc | null>(null)
  const [indexEditorOpen, setIndexEditorOpen] = useState(false)
  const [indexDocLoading, setIndexDocLoading] = useState(false)

  useEffect(() => {
    // Admin R13: embedded 且 external 都给了, 不 fetch
    if (embedded && externalProject && externalVersions && externalDocTree && externalBuilds) {
      setProject(externalProject)
      setVersions(externalVersions)
      setDocTree(externalDocTree)
      setBuilds(externalBuilds)
      setLoading(false)
      return
    }
    if (!projectId) return
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        const [projRes, verRes, buildsRes] = await Promise.all([
          projectApi.get(projectId),
          versionApi.list(projectId),
          buildApi.logs(projectId),
        ])
        if (cancelled) return
        setProject(projRes.data.data)
        setVersions(verRes.data.data || [])
        setBuilds(buildsRes.data.data || [])

        // 拉 default version 的 doc tree
        const vers = verRes.data.data || []
        const def = vers.find((v: any) => v.is_default) || vers[0]
        if (def) {
          const treeRes = await documentApi.tree(def.id)
          if (!cancelled) setDocTree(treeRes.data.data || [])
        }
      } catch (err: any) {
        if (!cancelled) setError(err?.response?.data?.detail || err?.message || '加载失败')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [projectId, embedded, externalProject, externalVersions, externalDocTree, externalBuilds])

  // 统计数据
  const stats = useMemo(() => {
    const flatten = (nodes: DocumentTreeNode[]): DocumentTreeNode[] => {
      const out: DocumentTreeNode[] = []
      const walk = (ns: DocumentTreeNode[]) => ns.forEach(n => {
        out.push(n)
        if (n.children?.length) walk(n.children)
      })
      walk(nodes)
      return out
    }
    const all = flatten(docTree)
    const folders = all.filter(n => n.is_folder)
    const docs = all.filter(n => !n.is_folder)
    const published = docs.filter(d => d.status === 'published').length
    const draft = docs.filter(d => d.status === 'draft').length
    const lastBuild = builds[0]
    return {
      folders: folders.length,
      docs: docs.length,
      published,
      draft,
      versionCount: versions.length,
      buildCount: builds.length,
      lastBuildAt: lastBuild?.created_at || null,
    }
  }, [docTree, versions, builds])

  // 段 C 收官: 拉 default version 的 slug=index doc
  // 触发条件: 父组件有 project.versions 数组, 找 is_default
  const defaultVersion = versions.find((v: any) => v.is_default) || versions[0]
  const fetchIndexDoc = async () => {
    if (!defaultVersion) {
      setIndexDoc(null)
      return
    }
    setIndexDocLoading(true)
    try {
      const r = await documentApi.tree(defaultVersion.id)
      // axios 包装: r.data = ApiResponse { data, meta }
      // ApiResponse.data = 后端 list_documents 返的 roots array
      const apiResp = (r as any).data
      const list = apiResp?.data || apiResp?.items || apiResp || []
      // documentApi.tree 返 doc 树 (可能含 folder), 过滤 slug=index
      const findIndex = (nodes: any[]): any | null => {
        for (const n of nodes) {
          if (n.slug === 'index' && !n.is_folder) return n
          if (n.children) {
            const f = findIndex(n.children)
            if (f) return f
          }
        }
        return null
      }
      const found = findIndex(Array.isArray(list) ? list : [])
      if (found) {
        // 拉详情拿 content
        const detail = await documentApi.get(found.id)
        const d = (detail as any).data?.data || (detail as any).data || detail
        setIndexDoc({
          id: d.id,
          title: d.title,
          slug: d.slug,
          content: d.content || '',
          status: d.status,
          updated_at: d.updated_at,
          version_id: d.version_id || defaultVersion.id,
        })
      } else {
        setIndexDoc(null)
      }
    } catch (e) {
      console.warn('fetchIndexDoc failed', e)
      setIndexDoc(null)
    } finally {
      setIndexDocLoading(false)
    }
  }

  useEffect(() => {
    if (defaultVersion) {
      fetchIndexDoc()
    }
  }, [defaultVersion?.id, project?.id])

  // Admin R13 2C: 4 张卡 (删 文件夹数), grid minmax(180px, 1fr) 适配 720px
  const cards: StatCard[] = [
    { label: '文档总数', value: stats.docs, icon: <FileTextOutlined />, color: '#4F46E5', tip: `其中 ${stats.draft} 篇草稿` },
    { label: '已发布', value: stats.published, icon: <CheckCircleOutlined />, color: '#34C759', tip: '在 published 站点可访问' },
    { label: '版本数', value: stats.versionCount, icon: <HistoryOutlined />, color: '#FF9500' },
    { label: '构建次数', value: stats.buildCount, icon: <RocketOutlined />, color: '#FF3B30', tip: stats.lastBuildAt ? `最近: ${formatDistanceToNow(new Date(stats.lastBuildAt))}` : '尚未构建' },
  ]

  // 树概览: 取前 8 个 root
  const rootNodes = useMemo(() => docTree.slice(0, 8), [docTree])
  const moreCount = Math.max(0, docTree.length - 8)

  // Admin R13 4A: 文档结构概览点击 — embedded 走 onSelectDoc, 否则 navigate
  const handleNodeClick = (node: DocumentTreeNode) => {
    if (onSelectDoc) {
      onSelectDoc(node.id)
    } else {
      navigate(`/projects/${project?.id}/docs`)
    }
  }

  // 渲染内容 (overview body)
  const overviewBody = (
    <div data-testid="project-overview" data-embedded={embedded ? 'true' : 'false'}>
      {/* Admin R13: 删顶部 breadcrumb + 返回 (embedded 模式不显示; 独立页也保留, 但其实没用了) */}

      {/* Admin R13 1A: 删品牌色 banner */}

      {/* 4 张统计卡 — Admin R13 2C */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 24 }}>
        {cards.map((c, i) => (
          <Tooltip key={i} title={c.tip}>
            <div
              data-testid={`stat-card-${c.label}`}
              style={{
                background: 'var(--bg-elevated, #fff)', border: '1px solid var(--border-subtle, #e5e5e7)',
                borderRadius: 12, padding: '20px 24px', cursor: 'default',
                transition: 'all 0.15s',
              }}
              onMouseEnter={(e) => (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)'}
              onMouseLeave={(e) => (e.currentTarget as HTMLElement).style.transform = 'translateY(0)'}
            >
              <Space align="center" size={8} style={{ marginBottom: 8 }}>
                <span style={{ color: c.color, fontSize: 18 }}>{c.icon}</span>
                <Text type="secondary" style={{ fontSize: 12 }}>{c.label}</Text>
              </Space>
              <div style={{ fontSize: 32, fontWeight: 600, color: 'var(--text-primary, #1a1a1a)', fontVariantNumeric: 'tabular-nums' }}>
                {c.value}
              </div>
            </div>
          </Tooltip>
        ))}
      </div>

      {/* Admin R13 4A: 文档树概览 — 保留 */}
      <div style={{
        background: 'var(--bg-elevated, #fff)', border: '1px solid var(--border-subtle, #e5e5e7)',
        borderRadius: 12, padding: '20px 24px', marginBottom: 16,
      }}>
        <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }}>
          <Space>
            <FileTextOutlined style={{ color: 'var(--brand-primary, #4F46E5)' }} />
            <Text strong style={{ fontSize: 14 }}>文档结构</Text>
            <Tag color="default">{docTree.length} 个根节点</Tag>
          </Space>
          {/* Admin R13: 删'查看全部'按钮 (已经在 /docs, 树就在侧栏) */}
        </Space>

        {rootNodes.length === 0 ? (
          <Empty description="暂无文档" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
            {rootNodes.map(node => (
              <div
                key={node.id}
                onClick={() => handleNodeClick(node)}
                style={{
                  border: '1px solid var(--border-subtle, #e5e5e7)', borderRadius: 8,
                  padding: '12px 16px', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: 10,
                  transition: 'all 0.15s',
                }}
                onMouseEnter={(e) => (e.currentTarget as HTMLElement).style.background = 'var(--hover-bg, #f5f5f7)'}
                onMouseLeave={(e) => (e.currentTarget as HTMLElement).style.background = 'transparent'}
              >
                <span style={{ color: 'var(--brand-primary, #4F46E5)', fontSize: 16 }}>
                  {node.is_folder ? <FolderOutlined /> : <FileTextOutlined />}
                </span>
                <span style={{ flex: 1, fontSize: 13, color: 'var(--text-primary, #1a1a1a)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {node.title}
                </span>
                {!node.is_folder && node.status === 'draft' && <Tag color="orange" style={{ fontSize: 10, margin: 0 }}>草稿</Tag>}
                {!node.is_folder && node.status === 'published' && <CheckCircleOutlined style={{ color: '#34C759', fontSize: 12 }} />}
                {node.is_folder && node.children && node.children.length > 0 && (
                  <Text type="secondary" style={{ fontSize: 11 }}>{node.children.length} 子项</Text>
                )}
              </div>
            ))}
          </div>
        )}
        {moreCount > 0 && (
          <div style={{ marginTop: 12, textAlign: 'center' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              还有 {moreCount} 个根节点 — 在左侧树查看全部
            </Text>
          </div>
        )}
      </div>

      {/* Admin R13 5A: 版本列表 — 保留 */}
      {versions.length > 0 && (
        <div style={{
          background: 'var(--bg-elevated, #fff)', border: '1px solid var(--border-subtle, #e5e5e7)',
          borderRadius: 12, padding: '20px 24px',
        }}>
          <Space style={{ marginBottom: 12 }}>
            <HistoryOutlined style={{ color: 'var(--brand-primary, #4F46E5)' }} />
            <Text strong style={{ fontSize: 14 }}>版本</Text>
            <Tag color="default">{versions.length} 个</Tag>
          </Space>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {versions.map((v: any) => (
              <div key={v.id} style={{
                border: '1px solid var(--border-subtle, #e5e5e7)', borderRadius: 8,
                padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 12,
              }}>
                <span style={{ fontFamily: 'monospace', fontSize: 13, color: 'var(--text-primary, #1a1a1a)' }}>
                  {v.version}
                </span>
                {v.is_default && <Tag color="blue" style={{ fontSize: 10, margin: 0 }}>默认</Tag>}
                {v.status === 'archived' && <Tag color="default" style={{ fontSize: 10, margin: 0 }}>已归档</Tag>}
                <Text type="secondary" style={{ fontSize: 11, marginLeft: 'auto' }}>
                  {v.created_at ? formatDistanceToNow(new Date(v.created_at)) : ''}
                </Text>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 段 C 收官: 首页配置 (slug=index doc) — Docusaurus 模式 */}
      <div data-testid="index-doc-card" style={{
        background: 'var(--bg-elevated, #fff)', border: '1px solid var(--border-subtle, #e5e5e7)',
        borderRadius: 12, padding: '20px 24px',
      }}>
        <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 12 }}>
          <Space>
            <HomeOutlined style={{ color: 'var(--brand-primary, #4F46E5)' }} />
            <Text strong style={{ fontSize: 14 }}>首页配置</Text>
            {indexDocLoading ? (
              <Tag>加载中</Tag>
            ) : indexDoc ? (
              <Tag color={indexDoc.status === 'published' ? 'green' : 'default'}>
                {indexDoc.status === 'published' ? '已发布' : '草稿'}
              </Tag>
            ) : (
              <Tag color="red">未找到</Tag>
            )}
          </Space>
          <Tooltip title={indexDoc ? '编辑 markdown Hero 内容' : '项目未建 index doc'}>
            <Button
              type="primary"
              icon={<EditOutlined />}
              disabled={!indexDoc}
              onClick={() => setIndexEditorOpen(true)}
              data-testid="open-index-editor"
            >
              {indexDoc ? '编辑 Hero' : '未配置'}
            </Button>
          </Tooltip>
        </Space>
        {indexDoc ? (
          <div style={{ fontSize: 12, color: 'var(--text-secondary, #666)' }}>
            <span>slug = </span>
            <code style={{ background: 'var(--bg-soft, #f5f5f7)', padding: '2px 6px', borderRadius: 4 }}>index</code>
            <span style={{ marginLeft: 12 }}>默认版本: </span>
            <code style={{ background: 'var(--bg-soft, #f5f5f7)', padding: '2px 6px', borderRadius: 4 }}>
              {defaultVersion?.version}
            </code>
            <span style={{ marginLeft: 12 }}>
              内容长度: {indexDoc.content.length} 字符
            </span>
            <div style={{ marginTop: 8, fontSize: 11 }}>
              {indexDoc.status === 'published'
                ? 'Hero 当前显示此文档内容(取决于最近一次 build)。点「编辑 Hero」修改后,记得点「重新构建」让静态站生效。'
                : 'Hero 当前显示默认 hardcode 内容。点「编辑 Hero」写 markdown, 然后「发布」并「重新构建」。'}
            </div>
          </div>
        ) : !indexDocLoading ? (
          <Empty
            description="未找到 slug=index 的首页配置文档"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            style={{ margin: '12px 0' }}
          >
            <Text type="secondary" style={{ fontSize: 11 }}>
              create_project 会自动建; 若是早期项目, 可在文档管理手动建一个 slug=index 的草稿。
            </Text>
          </Empty>
        ) : null}
      </div>
    </div>
  )

  // Admin R13: embedded 模式 — 直接返回内容 (没有 MainLayout wrapper, docs-main-header 已有)
  if (embedded) {
    if (loading) return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />
    if (error) return <Empty description={error} />
    if (!project) return <Empty description="项目不存在" />
    return (
      <>
        {overviewBody}
        <IndexDocEditor
          open={indexEditorOpen}
          onClose={() => setIndexEditorOpen(false)}
          indexDoc={indexDoc}
          projectSlug={project?.slug || ''}
          versionLabel={defaultVersion?.version || 'v1.0'}
          onSaved={setIndexDoc}
        />
      </>
    )
  }

  // 独立页模式 (R13 保留, 兼容老链接重定向前的短暂窗口)
  return (
    <MainLayout
      title={project?.name || '项目总览'}
      topSlot={project ? (
        <ProjectContextPanel
          name={project.name}
          versionCount={stats.versionCount}
        />
      ) : undefined}
    >
      {loading ? (
        <div style={{ padding: 80, textAlign: 'center' }}>
          <Spin size="large" />
        </div>
      ) : error ? (
        <Empty description={error} />
      ) : !project ? (
        <Empty description="项目不存在" />
      ) : (
        <div data-testid="project-overview-page">
          {/* 独立页模式: 保留 breadcrumb + 返回按钮 */}
          <Space style={{ marginBottom: 16 }}>
            <Button type="text" size="small" onClick={() => navigate('/projects')}>
              ← 返回项目列表
            </Button>
            <Breadcrumb>
              <Breadcrumb.Item><Link to="/projects">项目</Link></Breadcrumb.Item>
              <Breadcrumb.Item>{project.name}</Breadcrumb.Item>
            </Breadcrumb>
          </Space>
          {overviewBody}
        </div>
      )}
      <IndexDocEditor
        open={indexEditorOpen}
        onClose={() => setIndexEditorOpen(false)}
        indexDoc={indexDoc}
        projectSlug={project?.slug || ''}
        versionLabel={defaultVersion?.version || 'v1.0'}
        onSaved={setIndexDoc}
      />
    </MainLayout>
  )
}
