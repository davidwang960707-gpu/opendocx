/** AdminAudit — P1-W3-A2 审计日志
 *
 * 设计:
 * - 顶部: 标题 + action 过滤 (10 类) + actor 邮箱搜索 + reload
 * - 表格: 7 列 (时间 / 操作人 / 动作 / 目标类型 / 目标 ID / payload 摘要 / 展开详情)
 * - payload JSON Drawer: 完整 diff (改前/改后) / snapshot (删除)
 * - 公开操作 (feedback) actor_email='visitor:xxxx', actor_id=null
 *
 * 数据: GET /api/v1/audit-logs (admin 视角, 后端默认返最近 100 条)
 */
import { useEffect, useState, useMemo, useCallback, useRef } from 'react'
import {
  Table, Button, Space, Input, Tag, Select, Drawer, message, Typography, Tooltip,
  Empty, Skeleton,
} from 'antd'
import type { TableProps } from 'antd'
import {
  SearchOutlined, ReloadOutlined, EyeOutlined, UserOutlined, GlobalOutlined,
  HistoryOutlined,
} from '@ant-design/icons'
import { auditApi } from '../services/api'
import type { AuditLog } from '../types/api'
import MainLayout from '../layouts/MainLayout'

const { Text, Paragraph } = Typography

// 跟后端 audit hook 11 端点对齐
const ACTION_OPTIONS = [
  { label: '项目', value: 'project' },
  { label: '版本', value: 'version' },
  { label: '文档', value: 'document' },
  { label: '反馈', value: 'feedback' },
  { label: '用户', value: 'user' },
]

const ACTION_META: Record<string, { color: string; label: string }> = {
  'project.create': { color: 'green', label: '创建项目' },
  'project.update': { color: 'blue', label: '修改项目' },
  'project.delete': { color: 'red', label: '删除项目' },
  'version.create': { color: 'green', label: '创建版本' },
  'version.archive': { color: 'orange', label: '归档版本' },
  'version.set_default': { color: 'blue', label: '设默认版本' },
  'document.create': { color: 'green', label: '创建文档' },
  'document.update': { color: 'blue', label: '修改文档' },
  'document.delete': { color: 'red', label: '删除文档' },
  'feedback.create': { color: 'cyan', label: '读者反馈' },
  'feedback.delete': { color: 'red', label: '删除反馈' },
  'user.create': { color: 'green', label: '创建用户' },
  'user.update': { color: 'blue', label: '修改用户' },
  'user.delete': { color: 'red', label: '禁用用户' },
  'user.change_password': { color: 'purple', label: '改密' },
}

const ACTION_FILTERS = Object.entries(ACTION_META).map(([value, meta]) => ({
  text: meta.label,
  value,
}))

const TARGET_FILTERS = ACTION_OPTIONS.map(option => ({
  text: option.label,
  value: option.value,
}))

const fmtTime = (iso: string) => {
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', { hour12: false })
}

const summarizePayload = (log: AuditLog): string => {
  const p = log.payload || {}
  // 优先显示: title/name/slug/email/version/kind
  if (p.title) return p.title
  if (p.name) return p.name
  if (p.email) return p.email
  if (p.slug) return p.slug
  if (p.version) return p.version
  if (p.kind) return p.kind
  // diff
  if (p.changed_fields) return `改 ${p.changed_fields.join(', ')}`
  if (p.changes) return `${p.changes.length} 处改动`
  if (p.snapshot) return Object.keys(p.snapshot).join(', ')
  return '—'
}

const isVisitor = (log: AuditLog) => log.actor_id === null

const AUDIT_MIN_WIDTHS = {
  index: 48,
  time: 132,
  actor: 170,
  action: 112,
  target: 148,
  summary: 220,
  actions: 56,
}

const AUDIT_MIN_TOTAL = Object.values(AUDIT_MIN_WIDTHS).reduce((sum, width) => sum + width, 0)

const calcAuditColumnWidths = (containerWidth: number) => {
  const total = Math.max(Math.floor(containerWidth || 0), AUDIT_MIN_TOTAL)
  const extra = total - AUDIT_MIN_TOTAL

  const time = AUDIT_MIN_WIDTHS.time + Math.min(48, Math.floor(extra * 0.10))
  const actor = AUDIT_MIN_WIDTHS.actor + Math.min(110, Math.floor(extra * 0.18))
  const action = AUDIT_MIN_WIDTHS.action + Math.min(36, Math.floor(extra * 0.06))
  const target = AUDIT_MIN_WIDTHS.target + Math.min(72, Math.floor(extra * 0.12))
  const summary = Math.max(
    AUDIT_MIN_WIDTHS.summary,
    total - AUDIT_MIN_WIDTHS.index - time - actor - action - target - AUDIT_MIN_WIDTHS.actions
  )

  return {
    total,
    index: AUDIT_MIN_WIDTHS.index,
    time,
    actor,
    action,
    target,
    summary,
    actions: AUDIT_MIN_WIDTHS.actions,
  }
}

export default function AdminAudit() {
  const tableShellRef = useRef<HTMLDivElement | null>(null)
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [actionFilter, setActionFilter] = useState<string | undefined>()
  const [targetFilter, setTargetFilter] = useState<string | undefined>()
  const [actorFilter, setActorFilter] = useState('')
  const [detail, setDetail] = useState<AuditLog | null>(null)
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
  }, [logs.length])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await auditApi.list({
        page, page_size: pageSize,
        action: actionFilter,
        actor_email: actorFilter || undefined,
        target_type: targetFilter,
      })
      // 后端返 ApiResponse, axios 解一层; res.data = ApiResponse, 业务 data 在 res.data.data
      const resp: any = res.data
      const data = resp.data || resp
      setLogs(data.items || [])
      setTotal(data.total || 0)
    } catch (e: any) {
      message.error('加载审计日志失败: ' + (e?.response?.data?.detail || e?.message))
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, actionFilter, actorFilter, targetFilter])

  useEffect(() => { load() }, [load])

  const auditColumnWidths = useMemo(() => calcAuditColumnWidths(tableWidth), [tableWidth])

  const handleTableChange = useCallback<NonNullable<TableProps<AuditLog>['onChange']>>((_pagination, filters, _sorter, extra) => {
    if (extra.action !== 'filter') return

    const nextAction = Array.isArray(filters.action) ? filters.action[0] as string | undefined : undefined
    const nextTarget = Array.isArray(filters.target_type) ? filters.target_type[0] as string | undefined : undefined

    setActionFilter(nextAction)
    setTargetFilter(nextTarget)
    setPage(1)
  }, [])

  const columns = useMemo(() => [
    {
      title: '#',
      key: 'index',
      width: auditColumnWidths.index,
      align: 'center' as const,
      render: (_: any, __: any, idx: number) => (
        <Text type="secondary" style={{ fontSize: 12, fontFamily: 'var(--font-mono)' }}>
          {(page - 1) * pageSize + idx + 1}
        </Text>
      ),
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: auditColumnWidths.time,
      render: (t: string) => (
        <Text style={{ fontSize: 12, fontFamily: 'var(--font-mono)' }}>{fmtTime(t)}</Text>
      ),
    },
    {
      title: '操作人',
      dataIndex: 'actor_email',
      key: 'actor_email',
      width: auditColumnWidths.actor,
      ellipsis: true,
      render: (email: string, log: AuditLog) => (
        isVisitor(log) ? (
          <Tag color="cyan" style={{ margin: 0, maxWidth: 156, overflow: 'hidden', textOverflow: 'ellipsis' }}>
            <GlobalOutlined /> {email}
          </Tag>
        ) : (
          <Space size={4}>
            <UserOutlined style={{ color: 'var(--text-tertiary)' }} />
            <Text style={{ fontSize: 13, maxWidth: 140 }} ellipsis>{email}</Text>
          </Space>
        )
      ),
    },
    {
      title: '动作',
      dataIndex: 'action',
      key: 'action',
      width: auditColumnWidths.action,
      align: 'center' as const,
      filters: ACTION_FILTERS,
      filteredValue: actionFilter ? [actionFilter] : null,
      filterMultiple: false,
      render: (a: string) => {
        const meta = ACTION_META[a] || { color: 'default', label: a }
        return <Tag color={meta.color} style={{ margin: 0 }}>{meta.label}</Tag>
      },
    },
    {
      title: '目标',
      dataIndex: 'target_type',
      key: 'target_type',
      width: auditColumnWidths.target,
      filters: TARGET_FILTERS,
      filteredValue: targetFilter ? [targetFilter] : null,
      filterMultiple: false,
      render: (_targetType: string | null, l: AuditLog) => (
        <Space size={6}>
          {l.target_type && (
            <Tag style={{ margin: 0, fontSize: 11 }}>{l.target_type}</Tag>
          )}
          {l.target_id && (
            <Text type="secondary" style={{ fontSize: 11, fontFamily: 'var(--font-mono)' }}>
              {l.target_id.slice(0, 6)}…
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: '摘要',
      key: 'summary',
      width: auditColumnWidths.summary,
      ellipsis: true,
      render: (_: any, l: AuditLog) => (
        <Tooltip title={summarizePayload(l)}>
          <Text style={{ fontSize: 13 }} ellipsis>{summarizePayload(l)}</Text>
        </Tooltip>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: auditColumnWidths.actions,
      align: 'center' as const,
      render: (_: any, l: AuditLog) => (
        <Tooltip title="详情">
          <Button
            type="text"
            shape="circle"
            icon={<EyeOutlined />}
            aria-label="查看审计详情"
            onClick={() => setDetail(l)}
            data-testid={`audit-detail-btn-${l.id}`}
          />
        </Tooltip>
      ),
    },
  ], [actionFilter, auditColumnWidths, page, pageSize, targetFilter])

  return (
    <MainLayout subtitle="系统管理 · 审计日志" contentMaxWidth="full">
      <div className="page-toolbar">
        <div className="page-toolbar-left">
          <h1 className="page-title">
            <HistoryOutlined style={{ marginRight: 8 }} />
            审计日志
          </h1>
          <Text type="secondary" style={{ fontSize: 12 }}>
            共 {total} 条 · 公开操作 (feedback) 用 visitor 标识
          </Text>
        </div>
        <div className="page-toolbar-right">
          <Space size={16}>
            <Input
              allowClear
              prefix={<SearchOutlined style={{ color: 'var(--text-tertiary)' }} />}
              placeholder="操作人邮箱 / visitor"
              value={actorFilter}
              onChange={(e) => { setActorFilter(e.target.value); setPage(1) }}
              style={{ width: 240 }}
              data-testid="audit-actor-search"
            />
            <Select
              allowClear
              placeholder="动作类型"
              value={actionFilter}
              onChange={(v) => { setActionFilter(v); setPage(1) }}
              style={{ width: 140 }}
              options={ACTION_OPTIONS.flatMap(prefix =>
                Object.keys(ACTION_META)
                  .filter(a => a.startsWith(prefix.value + '.'))
                  .map(a => ({ label: ACTION_META[a].label, value: a }))
              )}
              data-testid="audit-action-filter"
            />
            <Button icon={<ReloadOutlined />} onClick={load} data-testid="audit-reload-btn" />
          </Space>
        </div>
      </div>

      {loading && logs.length === 0 ? (
        <Skeleton active style={{ padding: 24 }} />
      ) : logs.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={actionFilter || actorFilter || targetFilter ? '没有匹配的审计记录' : '还没有任何审计记录'}
          style={{ padding: 60 }}
        />
      ) : (
        <div className="admin-table-shell admin-table-shell--audit" ref={tableShellRef}>
          <Table
            rowKey="id"
            dataSource={logs}
            columns={columns as any}
            loading={loading}
            pagination={{
              current: page, pageSize, total,
              showSizeChanger: true, pageSizeOptions: ['10', '20', '50', '100'],
              onChange: (p, ps) => { setPage(p); setPageSize(ps) },
              showTotal: (t) => `共 ${t} 条`,
            }}
            onChange={handleTableChange}
            scroll={{ x: auditColumnWidths.total }}
            tableLayout="fixed"
            data-testid="audit-table"
          />
        </div>
      )}

      <Drawer
        title="审计详情"
        width={680}
        open={!!detail}
        onClose={() => setDetail(null)}
        data-testid="audit-detail-drawer"
      >
        {detail && (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>时间</Text>
              <Paragraph style={{ margin: 0, fontFamily: 'var(--font-mono)', fontSize: 13 }}>
                {fmtTime(detail.created_at)}
              </Paragraph>
            </div>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>操作人</Text>
              <Paragraph style={{ margin: 0, fontSize: 13 }}>
                {detail.actor_email}
                {detail.actor_id && (
                  <Text type="secondary" style={{ fontSize: 11, marginLeft: 8 }}>
                    (id: {detail.actor_id.slice(0, 8)}…)
                  </Text>
                )}
                {isVisitor(detail) && (
                  <Tag color="cyan" style={{ marginLeft: 8 }}>公开操作</Tag>
                )}
              </Paragraph>
            </div>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>动作</Text>
              <Paragraph style={{ margin: 0 }}>
                <Tag color={ACTION_META[detail.action]?.color || 'default'}>
                  {ACTION_META[detail.action]?.label || detail.action}
                </Tag>
              </Paragraph>
            </div>
            {detail.target_type && (
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>目标</Text>
                <Paragraph style={{ margin: 0, fontSize: 13 }}>
                  <Tag>{detail.target_type}</Tag>
                  <Text style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{detail.target_id}</Text>
                </Paragraph>
              </div>
            )}
            {detail.payload && (
              <div>
                <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>Payload</Text>
                {/* V2-C: 自渲 pre 替换 Antd Alert (Admin反馈 "ant-alert-content 丑") */}
                <pre
                  data-testid="audit-detail-payload"
                  style={{
                    margin: 0, padding: '14px 16px', maxHeight: 480, overflow: 'auto',
                    fontFamily: 'var(--font-mono)', fontSize: 12, lineHeight: 1.6,
                    background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-subtle)',
                    color: 'var(--text-primary)',
                  }}
                >
                  {JSON.stringify(detail.payload, null, 2)}
                </pre>
              </div>
            )}
          </Space>
        )}
      </Drawer>
    </MainLayout>
  )
}
