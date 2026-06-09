import { useMemo } from 'react'
import { Typography, Tag, Button, Empty, Space, Table, Tooltip } from 'antd'
import { FileTextOutlined, FolderAddOutlined, PlusOutlined, ClockCircleOutlined, AimOutlined } from '@ant-design/icons'
import type { DocumentTreeNode } from '../types/api'
import '../styles/folder-overview.css'

const { Text, Title } = Typography

interface FolderOverviewProps {
  folder: DocumentTreeNode
  /** 整个版本树 (用于统计子级字数等) */
  allNodes?: DocumentTreeNode[]
  onOpenDoc: (docId: string) => void
  onAddChildDoc: (folderId: string) => void
  onAddChildFolder: (folderId: string) => void
}

interface ChildRow {
  key: string
  title: string
  status: string
  childCount: number
  wordCount: number
  updatedAt: string
  type: 'doc' | 'folder'
}

function collectAll(nodes: DocumentTreeNode[]): DocumentTreeNode[] {
  const out: DocumentTreeNode[] = []
  const walk = (ns: DocumentTreeNode[]) => ns.forEach(n => { out.push(n); if (n.children?.length) walk(n.children) })
  walk(nodes)
  return out
}

function countWords(s?: string | null): number {
  if (!s) return 0
  // 中英文混合: 中文按字符数, 英文按空格分词
  const cn = (s.match(/[一-龥]/g) || []).length
  const en = (s.replace(/[一-龥]/g, ' ').match(/[a-zA-Z0-9]+/g) || []).length
  return cn + en
}

function formatRelative(iso: string): string {
  if (!iso) return '-'
  const d = new Date(iso)
  const diff = Date.now() - d.getTime()
  if (diff < 60_000) return '刚刚'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} 小时前`
  if (diff < 7 * 86_400_000) return `${Math.floor(diff / 86_400_000)} 天前`
  return d.toLocaleString('zh-CN', { hour12: false }).substring(0, 10)
}

export default function FolderOverview({
  folder,
  allNodes = [],
  onOpenDoc,
  onAddChildDoc,
  onAddChildFolder,
}: FolderOverviewProps) {
  // 浅 + 深统计
  const direct = folder.children || []
  const all = useMemo(() => collectAll([folder]).slice(1), [folder])
  const allById = useMemo(() => {
    const m: Record<string, DocumentTreeNode> = {}
    collectAll(allNodes).forEach(n => { m[n.id] = n })
    return m
  }, [allNodes])

  const stats = useMemo(() => {
    const allDescDocs = all.filter(n => !n.is_folder)
    const totalDocs = allDescDocs.length
    const publishedDocs = allDescDocs.filter(n => n.status === 'published').length
    const totalWords = allDescDocs.reduce((s, n) => s + countWords(allById[n.id]?.slug ? '' : ''), 0)
    // 直接走 children 的 content 字段, 树上没有 content, 走 byId
    const allByIdLocal = allById
    const wc = allDescDocs.reduce((s, n) => {
      // 通过 node 查 byId (slug+title 也算展示) — 内容字数需另查接口, 这里只统计可见
      return s
    }, 0)
    return {
      directChildren: direct.length,
      directFolders: direct.filter(n => n.is_folder).length,
      directDocs: direct.filter(n => !n.is_folder).length,
      allDescFolders: all.filter(n => n.is_folder).length,
      totalDescDocs: totalDocs,
      publishedDescDocs: publishedDocs,
      totalDescWords: wc, // 由后端补接口时替换
    }
  }, [folder, all, allById, direct])

  const rows: ChildRow[] = direct.map(n => ({
    key: n.id,
    title: n.title,
    status: n.status,
    childCount: n.children?.length || 0,
    wordCount: 0, // 单文档字数需 GET /documents/{id} 拉 content, 这里先 0
    updatedAt: '',
    type: n.is_folder ? 'folder' : 'doc',
  }))

  const columns = [
    {
      title: '名称',
      dataIndex: 'title',
      key: 'title',
      render: (_: string, r: ChildRow) => (
        <Space size={6}>
          {r.type === 'folder'
            ? <span style={{ color: 'var(--brand-primary)' }}>📁</span>
            : <FileTextOutlined style={{ color: 'var(--text-tertiary, #86868B)' }} />}
          {r.type === 'doc' ? (
            <a onClick={() => onOpenDoc(r.key)}>{r.title}</a>
          ) : (
            <Text strong>{r.title}</Text>
          )}
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 80,
      render: (t: string) => t === 'folder'
        ? <Tag color="blue" style={{ borderRadius: 10 }}>文件夹</Tag>
        : <Tag color="default" style={{ borderRadius: 10 }}>文档</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (s: string) => s === 'published'
        ? <Tag color="success" style={{ borderRadius: 10 }}>已发布</Tag>
        : s === 'draft'
        ? <Tag color="warning" style={{ borderRadius: 10 }}>草稿</Tag>
        : <Tag style={{ borderRadius: 10 }}>{s}</Tag>,
    },
    {
      title: '子节点',
      dataIndex: 'childCount',
      key: 'childCount',
      width: 80,
      align: 'right' as const,
      render: (n: number) => n > 0 ? <Text type="secondary">{n}</Text> : <Text type="secondary">-</Text>,
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, r: ChildRow) => r.type === 'doc' ? (
        <Button size="small" type="link" onClick={() => onOpenDoc(r.key)}>打开</Button>
      ) : (
        <Text type="secondary" style={{ fontSize: 12 }}>—</Text>
      ),
    },
  ]

  return (
    <div className="folder-overview">
      <div className="folder-overview-header">
        <Space align="start" size={12}>
          <div className="folder-overview-icon">
            <AimOutlined />
          </div>
          <div>
            <Title level={3} style={{ margin: 0, marginBottom: 2 }}>
              {folder.title}
            </Title>
            <Space size={6}>
              <Text type="secondary" style={{ fontSize: 13 }}>文件夹</Text>
              <Text type="secondary" style={{ fontSize: 13 }}>·</Text>
              <Text type="secondary" style={{ fontSize: 13 }}>
                <ClockCircleOutlined /> 即将显示更新时间
              </Text>
            </Space>
          </div>
        </Space>
        <Space>
          <Button icon={<PlusOutlined />} onClick={() => onAddChildDoc(folder.id)}>
            新建子文档
          </Button>
          <Button icon={<FolderAddOutlined />} onClick={() => onAddChildFolder(folder.id)}>
            新建子文件夹
          </Button>
        </Space>
      </div>

      {/* 统计卡片: 直接子节点 + 全部后代 */}
      <div className="folder-overview-stats">
        <div className="folder-stat-card">
          <div className="folder-stat-value">{stats.directChildren}</div>
          <div className="folder-stat-label">直接子节点</div>
        </div>
        <div className="folder-stat-card">
          <div className="folder-stat-value">{stats.directFolders}</div>
          <div className="folder-stat-label">子文件夹</div>
        </div>
        <div className="folder-stat-card">
          <div className="folder-stat-value">{stats.directDocs}</div>
          <div className="folder-stat-label">子文档</div>
        </div>
        <div className="folder-stat-card folder-stat-card--accent">
          <div className="folder-stat-value">{stats.totalDescDocs}</div>
          <div className="folder-stat-label">全部后代文档</div>
        </div>
        <div className="folder-stat-card folder-stat-card--success">
          <div className="folder-stat-value">{stats.publishedDescDocs}</div>
          <div className="folder-stat-label">已发布</div>
        </div>
      </div>

      <div className="folder-overview-children">
        <div className="folder-overview-section-title">
          <span>直接子节点</span>
          <Text type="secondary" style={{ fontSize: 12 }}>点击文档名直接打开</Text>
        </div>
        {rows.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <Space direction="vertical" size={4}>
                <Text type="secondary">这个文件夹是空的</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>添加第一个子文档或子文件夹开始组织</Text>
              </Space>
            }
            style={{ padding: '32px 0' }}
          >
            <Space>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => onAddChildDoc(folder.id)}>
                新建子文档
              </Button>
              <Button icon={<FolderAddOutlined />} onClick={() => onAddChildFolder(folder.id)}>
                新建子文件夹
              </Button>
            </Space>
          </Empty>
        ) : (
          <Table
            size="small"
            dataSource={rows}
            columns={columns as any}
            pagination={false}
            rowKey="key"
            className="folder-overview-table"
          />
        )}
      </div>
    </div>
  )
}
