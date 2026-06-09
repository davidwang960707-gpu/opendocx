/**
 * AdminFeedbacks — 反馈审核页
 *
 * 后台 /admin/feedbacks 路由:
 * - 全量反馈列表
 * - 类型 / 文档 / visitor/user_name 过滤
 * - admin 删除反馈
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Button,
  Col,
  Empty,
  Input,
  message,
  Popconfirm,
  Row,
  Space,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd'
import type { TableProps } from 'antd'
import {
  DeleteOutlined,
  DislikeOutlined,
  LikeOutlined,
  MessageOutlined,
  ReloadOutlined,
  SearchOutlined,
  StarOutlined,
} from '@ant-design/icons'
import MainLayout from '../layouts/MainLayout'
import { feedbackApi } from '../services/api'

const { Text, Paragraph } = Typography

interface FeedbackRow {
  id: string
  document_id: string
  version_id: string
  kind: 'like' | 'dislike' | 'bookmark' | 'comment'
  visitor_id: string
  user_id: string | null
  user_name: string | null
  body: string | null
  parent_id: string | null
  created_at: string | null
}

const KIND_LABEL: Record<FeedbackRow['kind'], { label: string; color: string; icon: React.ReactNode }> = {
  like: { label: '点赞', color: 'green', icon: <LikeOutlined /> },
  dislike: { label: '点踩', color: 'red', icon: <DislikeOutlined /> },
  bookmark: { label: '收藏', color: 'gold', icon: <StarOutlined /> },
  comment: { label: '评论', color: 'blue', icon: <MessageOutlined /> },
}

const KIND_FILTERS = Object.entries(KIND_LABEL).map(([value, meta]) => ({
  text: meta.label,
  value,
}))

const FEEDBACK_MIN_WIDTHS = {
  kind: 98,
  body: 300,
  author: 180,
  document: 128,
  time: 156,
  actions: 56,
}

const FEEDBACK_MIN_TOTAL = Object.values(FEEDBACK_MIN_WIDTHS).reduce((sum, width) => sum + width, 0)

const calcFeedbackColumnWidths = (containerWidth: number) => {
  const total = Math.max(Math.floor(containerWidth || 0), FEEDBACK_MIN_TOTAL)
  const extra = total - FEEDBACK_MIN_TOTAL
  const author = FEEDBACK_MIN_WIDTHS.author + Math.min(120, Math.floor(extra * 0.18))
  const document = FEEDBACK_MIN_WIDTHS.document + Math.min(70, Math.floor(extra * 0.10))
  const time = FEEDBACK_MIN_WIDTHS.time + Math.min(44, Math.floor(extra * 0.08))
  const body = Math.max(
    FEEDBACK_MIN_WIDTHS.body,
    total - FEEDBACK_MIN_WIDTHS.kind - author - document - time - FEEDBACK_MIN_WIDTHS.actions
  )

  return {
    total,
    kind: FEEDBACK_MIN_WIDTHS.kind,
    body,
    author,
    document,
    time,
    actions: FEEDBACK_MIN_WIDTHS.actions,
  }
}

export default function AdminFeedbacks() {
  const tableShellRef = useRef<HTMLDivElement | null>(null)
  const [rows, setRows] = useState<FeedbackRow[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [kindFilter, setKindFilter] = useState<string | undefined>()
  const [documentFilter, setDocumentFilter] = useState<string | undefined>()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [tableWidth, setTableWidth] = useState(0)

  useEffect(() => {
    const el = tableShellRef.current
    if (!el) return

    const updateWidth = () => setTableWidth(Math.floor(el.getBoundingClientRect().width))
    updateWidth()

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (entry) setTableWidth(Math.floor(entry.contentRect.width))
    })
    resizeObserver.observe(el)
    return () => resizeObserver.disconnect()
  }, [rows.length])

  const fetchList = useCallback(async () => {
    setLoading(true)
    try {
      const params: any = { limit: pageSize, offset: (page - 1) * pageSize }
      if (kindFilter) params.kind = kindFilter
      if (documentFilter) params.document_id = documentFilter
      if (search.trim()) params.user_email = search.trim()
      const res: any = await feedbackApi.adminList(params)
      const data = res?.data?.data || res?.data || res
      setRows(data?.items || [])
      setTotal(data?.total || 0)
    } catch (e: any) {
      message.error('加载反馈失败: ' + (e?.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }, [documentFilter, kindFilter, page, pageSize, search])

  useEffect(() => { fetchList() }, [fetchList])

  const stats = useMemo(() => {
    const counts: Record<string, number> = {}
    rows.forEach(row => { counts[row.kind] = (counts[row.kind] || 0) + 1 })
    return counts
  }, [rows])

  const documentFilters = useMemo(() => {
    const ids = Array.from(new Set(rows.map(row => row.document_id).filter(Boolean)))
    return ids.map(id => ({ text: id.slice(0, 8), value: id }))
  }, [rows])

  const feedbackColumnWidths = useMemo(() => calcFeedbackColumnWidths(tableWidth), [tableWidth])

  const handleDelete = async (id: string) => {
    try {
      await feedbackApi.adminDelete(id)
      message.success('已删除')
      fetchList()
    } catch (e: any) {
      message.error('删除失败: ' + (e?.message || '未知错误'))
    }
  }

  const handleTableChange = useCallback<NonNullable<TableProps<FeedbackRow>['onChange']>>((_pagination, filters, _sorter, extra) => {
    if (extra.action !== 'filter') return

    const nextKind = Array.isArray(filters.kind) ? filters.kind[0] as string | undefined : undefined
    const nextDocument = Array.isArray(filters.document_id) ? filters.document_id[0] as string | undefined : undefined
    setKindFilter(nextKind)
    setDocumentFilter(nextDocument)
    setPage(1)
  }, [])

  const columns = useMemo<TableProps<FeedbackRow>['columns']>(() => [
    {
      title: '类型',
      dataIndex: 'kind',
      key: 'kind',
      width: feedbackColumnWidths.kind,
      filters: KIND_FILTERS,
      filteredValue: kindFilter ? [kindFilter] : null,
      filterMultiple: false,
      render: (kind: FeedbackRow['kind']) => {
        const meta = KIND_LABEL[kind]
        return <Tag color={meta.color} icon={meta.icon} style={{ margin: 0 }}>{meta.label}</Tag>
      },
    },
    {
      title: '内容',
      dataIndex: 'body',
      key: 'body',
      width: feedbackColumnWidths.body,
      ellipsis: true,
      render: (body: string | null, row) => {
        if (!body) return <Text type="secondary" style={{ fontSize: 12 }}>(无文本内容)</Text>
        return (
          <div className="feedback-body-cell">
            <Paragraph style={{ marginBottom: 4, fontSize: 13 }} ellipsis={{ rows: 2 }}>
              {body}
            </Paragraph>
            {row.parent_id && (
              <Text type="secondary" style={{ fontSize: 11 }}>
                <Tooltip title={row.parent_id}>回复评论 #{row.parent_id.slice(0, 8)}</Tooltip>
              </Text>
            )}
          </div>
        )
      },
    },
    {
      title: '作者',
      dataIndex: 'user_name',
      key: 'user_name',
      width: feedbackColumnWidths.author,
      ellipsis: true,
      render: (name: string | null, row) => (
        <div className="feedback-author-cell">
          <Text style={{ fontSize: 12 }}>{name || '匿名读者'}</Text>
          <Tooltip title={row.visitor_id}>
            <Text type="secondary" style={{ fontSize: 11 }} ellipsis>visitor: {row.visitor_id}</Text>
          </Tooltip>
        </div>
      ),
    },
    {
      title: '文档',
      dataIndex: 'document_id',
      key: 'document_id',
      width: feedbackColumnWidths.document,
      filters: documentFilters,
      filteredValue: documentFilter ? [documentFilter] : null,
      filterMultiple: false,
      render: (id: string) => (
        <Tooltip title={id}>
          <Text code style={{ fontSize: 11 }}>{id.slice(0, 8)}</Text>
        </Tooltip>
      ),
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: feedbackColumnWidths.time,
      render: (time: string | null) => (
        <Text style={{ fontSize: 12, fontFamily: 'var(--font-mono)' }}>
          {time ? new Date(time).toLocaleString('zh-CN', { hour12: false }) : '-'}
        </Text>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: feedbackColumnWidths.actions,
      align: 'center',
      render: (_, row) => (
        <Popconfirm
          title="确认删除该反馈?"
          description="删除后无法恢复，并会写入审计日志"
          okButtonProps={{ danger: true }}
          onConfirm={() => handleDelete(row.id)}
        >
          <Tooltip title="删除">
            <Button
              type="text"
              shape="circle"
              danger
              icon={<DeleteOutlined />}
              aria-label="删除反馈"
            />
          </Tooltip>
        </Popconfirm>
      ),
    },
  ], [documentFilter, documentFilters, feedbackColumnWidths, kindFilter])

  return (
    <MainLayout subtitle="系统管理 · 反馈审核" contentMaxWidth="full">
      <div className="page-toolbar">
        <div className="page-toolbar-left">
          <h1 className="page-title">
            <MessageOutlined style={{ marginRight: 8 }} />
            反馈审核
          </h1>
          <Text type="secondary" style={{ fontSize: 12 }}>
            共 {total} 条 · 公开评论用 visitor 标识 · admin/editor 角色可访问
          </Text>
        </div>
        <div className="page-toolbar-right">
          <Space size={16}>
            <Input
              allowClear
              prefix={<SearchOutlined style={{ color: 'var(--text-tertiary)' }} />}
              placeholder="搜索 visitor / 用户名"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onPressEnter={() => { setPage(1); fetchList() }}
              style={{ width: 240 }}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchList}>刷新</Button>
          </Space>
        </div>
      </div>

      <Row gutter={12} className="feedback-stats-row">
        <Col xs={12} lg={6}>
          <div className="feedback-stat-card">
            <Statistic title="本页点赞" value={stats.like || 0} valueStyle={{ color: '#52c41a' }} prefix={<LikeOutlined />} />
          </div>
        </Col>
        <Col xs={12} lg={6}>
          <div className="feedback-stat-card">
            <Statistic title="本页点踩" value={stats.dislike || 0} valueStyle={{ color: '#ff4d4f' }} prefix={<DislikeOutlined />} />
          </div>
        </Col>
        <Col xs={12} lg={6}>
          <div className="feedback-stat-card">
            <Statistic title="本页收藏" value={stats.bookmark || 0} valueStyle={{ color: '#faad14' }} prefix={<StarOutlined />} />
          </div>
        </Col>
        <Col xs={12} lg={6}>
          <div className="feedback-stat-card">
            <Statistic title="本页评论" value={stats.comment || 0} valueStyle={{ color: '#1890ff' }} prefix={<MessageOutlined />} />
          </div>
        </Col>
      </Row>

      <div className="admin-table-shell admin-table-shell--feedback" ref={tableShellRef}>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={rows}
          loading={loading}
          locale={{ emptyText: <Empty description={kindFilter || documentFilter || search ? '没有匹配的反馈' : '暂无反馈'} /> }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50', '100'],
            onChange: (nextPage, nextPageSize) => { setPage(nextPage); setPageSize(nextPageSize) },
            showTotal: (count) => `共 ${count} 条`,
          }}
          onChange={handleTableChange}
          scroll={{ x: feedbackColumnWidths.total }}
          tableLayout="fixed"
          size="small"
        />
      </div>
    </MainLayout>
  )
}
