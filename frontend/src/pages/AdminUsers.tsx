/** AdminUsers — P1-W3-A2 系统管理用户列表 */
import { useEffect, useState, useCallback } from 'react'
import {
  Button, Space, Input, Tag, Switch, Popconfirm, Drawer, Form, Select,
  message, Avatar, Typography, Tooltip, Empty, Skeleton, Alert,
} from 'antd'
import {
  PlusOutlined, SearchOutlined, UserOutlined, EditOutlined, DeleteOutlined,
  KeyOutlined, CopyOutlined, ReloadOutlined, MailOutlined, ClockCircleOutlined,
} from '@ant-design/icons'
import { userApi } from '../services/api'
import type { UserFull, UserCreateResponse } from '../types/api'
import { useAuthStore } from '../stores/auth'
import MainLayout from '../layouts/MainLayout'

const { Text, Paragraph } = Typography

const ROLE_META: Record<string, { label: string; color: string }> = {
  admin: { label: '管理员', color: 'red' },
  editor: { label: '编辑', color: 'blue' },
  viewer: { label: '只读', color: 'default' },
}

const fmtTime = (iso: string | null) => {
  if (!iso) return '从未'
  const d = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  const min = Math.floor(diff / 60000)
  if (min < 1) return '刚刚'
  if (min < 60) return `${min} 分钟前`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr} 小时前`
  const day = Math.floor(hr / 24)
  if (day < 30) return `${day} 天前`
  return d.toLocaleDateString('zh-CN')
}

interface DrawerState {
  open: boolean
  mode: 'create' | 'edit'
  user: UserFull | null
}

export default function AdminUsers() {
  const me = useAuthStore(s => s.user)
  const [users, setUsers] = useState<UserFull[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState<string | undefined>()
  const [drawer, setDrawer] = useState<DrawerState>({ open: false, mode: 'create', user: null })
  const [createdPwd, setCreatedPwd] = useState<string | null>(null)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await userApi.list({
        page, page_size: pageSize,
        search: search || undefined,
        role: roleFilter,
      })
      // 后端返 ApiResponse, axios 解一层; res.data = ApiResponse, 业务 data 在 res.data.data
      const resp: any = res.data
      const data = resp.data || resp  // 兼容未包 ApiResponse
      setUsers(data.items || [])
      setTotal(data.total || 0)
    } catch (e: any) {
      message.error('加载用户失败: ' + (e?.response?.data?.detail || e?.message))
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, search, roleFilter])

  useEffect(() => { load() }, [load])

  const openCreate = () => {
    form.resetFields()
    form.setFieldsValue({ role: 'viewer', is_active: true })
    setCreatedPwd(null)
    setDrawer({ open: true, mode: 'create', user: null })
  }

  const openEdit = (u: UserFull) => {
    form.setFieldsValue({
      email: u.email, name: u.name, role: u.role, is_active: u.is_active,
    })
    setCreatedPwd(null)
    setDrawer({ open: true, mode: 'edit', user: u })
  }

  const submit = async () => {
    try {
      const v = await form.validateFields()
      if (drawer.mode === 'create') {
        const res = await userApi.create(v)
        const resp: any = res.data
        const data: UserCreateResponse = resp.data
        setCreatedPwd(data.temporary_password)
        message.success('用户已创建, 临时密码已显示在下方')
        await load()
        form.setFieldsValue({
          email: data.user.email, name: data.user.name,
          role: data.user.role, is_active: data.user.is_active,
        })
        setDrawer({ open: true, mode: 'edit', user: data.user })
      } else if (drawer.user) {
        await userApi.update(drawer.user.id, v)
        message.success('已保存')
        setDrawer({ open: false, mode: 'create', user: null })
        setCreatedPwd(null)
        await load()
      }
    } catch (e: any) {
      if (e?.errorFields) return
      message.error('保存失败: ' + (e?.response?.data?.detail || e?.message))
    }
  }

  const toggleActive = async (u: UserFull, checked: boolean) => {
    try {
      await userApi.update(u.id, { is_active: checked })
      message.success(checked ? '已启用' : '已禁用')
      await load()
    } catch (e: any) {
      message.error('操作失败: ' + (e?.response?.data?.detail || e?.message))
    }
  }

  const remove = async (u: UserFull) => {
    if (u.id === me?.id) {
      message.error('不能删除自己')
      return
    }
    try {
      await userApi.delete(u.id)
      message.success('已禁用账号')
      await load()
    } catch (e: any) {
      message.error('删除失败: ' + (e?.response?.data?.detail || e?.message))
    }
  }

  const copy = (text: string) => {
    navigator.clipboard.writeText(text).then(
      () => message.success('已复制到剪贴板'),
      () => message.error('复制失败'),
    )
  }

  return (
    <MainLayout subtitle="系统管理 · 用户与权限" contentMaxWidth="full">
      <div className="page-toolbar">
        <div className="page-toolbar-left">
          <h1 className="page-title">用户管理</h1>
          <Text type="secondary" style={{ fontSize: 12 }} data-testid="user-count">
            共 {total} 个账号 · {users.filter(u => u.is_active).length} 个启用
          </Text>
        </div>
        <div className="page-toolbar-right">
          <Space size={16}>
            <Input
              allowClear
              prefix={<SearchOutlined style={{ color: 'var(--text-tertiary)' }} />}
              placeholder="搜索邮箱或姓名"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
              style={{ width: 240 }}
              data-testid="user-search-input"
            />
            <Select
              allowClear
              placeholder="角色"
              value={roleFilter}
              onChange={(v) => { setRoleFilter(v); setPage(1) }}
              style={{ width: 120 }}
              options={[
                { label: '管理员', value: 'admin' },
                { label: '编辑', value: 'editor' },
                { label: '只读', value: 'viewer' },
              ]}
              data-testid="user-role-filter"
            />
            <Button icon={<ReloadOutlined />} onClick={load} data-testid="user-reload-btn" />
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} data-testid="user-create-btn">
              新建用户
            </Button>
          </Space>
        </div>
      </div>

      {loading && users.length === 0 ? (
        <Skeleton active style={{ padding: 24 }} />
      ) : users.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={search || roleFilter ? '没有匹配的用户' : '还没有任何用户, 点右上角新建'}
          style={{ padding: 60 }}
        />
      ) : (
        <div className="admin-table-shell" data-testid="user-table">
          {users.map(u => (
            <div
              key={u.id}
              className="admin-user-row"
              data-testid={`user-row-${u.id}`}
            >
              <Space size={10}>
                <Avatar size={28} style={{ background: 'var(--brand-color, #4F46E5)', fontSize: 12 }}>
                  {u.name?.[0]?.toUpperCase() || u.email[0]?.toUpperCase()}
                </Avatar>
                <div>
                  <div style={{ fontWeight: 500 }}>{u.name || '—'}</div>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    <MailOutlined style={{ marginRight: 4 }} />
                    {u.email}
                  </Text>
                </div>
              </Space>
              <div>
                <Tag color={ROLE_META[u.role]?.color || 'default'} style={{ margin: 0, fontSize: 11 }}>
                  {ROLE_META[u.role]?.label || u.role}
                </Tag>
              </div>
              <div>
                <Tooltip title={u.is_active ? '点击禁用' : '点击启用'}>
                  <Switch
                    checked={u.is_active}
                    disabled={u.id === me?.id}
                    onChange={(c) => toggleActive(u, c)}
                    data-testid={`user-active-switch-${u.id}`}
                  />
                </Tooltip>
              </div>
              <Tooltip title={u.last_login_at ? new Date(u.last_login_at).toLocaleString('zh-CN') : '从未登录'}>
                <Text type={u.last_login_at ? undefined : 'secondary'} style={{ fontSize: 12 }}>
                  <ClockCircleOutlined style={{ marginRight: 4 }} />
                  {fmtTime(u.last_login_at)}
                </Text>
              </Tooltip>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {new Date(u.created_at).toLocaleDateString('zh-CN')}
              </Text>
              <div className="admin-row-actions">
                <Tooltip title="编辑">
                  <Button
                    type="text" icon={<EditOutlined />}
                    onClick={() => openEdit(u)}
                    data-testid={`user-edit-btn-${u.id}`}
                  />
                </Tooltip>
                <Popconfirm
                  title={u.id === me?.id ? '不能删除自己' : '禁用此账号?'}
                  description={u.id === me?.id ? '请先退出当前账号' : '该用户将无法登录 (软删 is_active=false)'}
                  okText="确认禁用"
                  cancelText="取消"
                  okButtonProps={{ danger: true, disabled: u.id === me?.id }}
                  onConfirm={() => remove(u)}
                >
                  <Tooltip title={u.id === me?.id ? '不能删除自己' : '禁用'}>
                    <Button
                      type="text" danger icon={<DeleteOutlined />}
                      disabled={u.id === me?.id}
                      data-testid={`user-delete-btn-${u.id}`}
                    />
                  </Tooltip>
                </Popconfirm>
              </div>
            </div>
          ))}
          {total > pageSize && (
            <div style={{ padding: 16, textAlign: 'center' }}>
              <Text type="secondary" style={{ fontSize: 11 }}>
                第 {page} 页 / 共 {total} 个 (分页待 W4 接入 antd Pagination)
              </Text>
            </div>
          )}
        </div>
      )}

      <Drawer
        title={drawer.mode === 'create' ? '新建用户' : `编辑用户 · ${drawer.user?.email}`}
        width={560}
        open={drawer.open}
        onClose={() => { setDrawer({ open: false, mode: 'create', user: null }); setCreatedPwd(null) }}
        extra={
          <Space>
            <Button onClick={() => { setDrawer({ open: false, mode: 'create', user: null }); setCreatedPwd(null) }}>
              取消
            </Button>
            <Button type="primary" onClick={submit} data-testid="user-drawer-submit">
              {drawer.mode === 'create' ? '创建' : '保存'}
            </Button>
          </Space>
        }
        data-testid="user-drawer"
      >
        {createdPwd && (
          <Alert
            type="success"
            showIcon
            style={{ marginBottom: 20 }}
            message={
              <Space>
                <KeyOutlined />
                <Text strong>临时密码 (一次性显示):</Text>
                <Paragraph
                  copyable={{ text: createdPwd, tooltips: ['复制', '已复制'] }}
                  style={{ margin: 0, fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 600 }}
                >
                  {createdPwd}
                </Paragraph>
              </Space>
            }
            description={
              <Text type="secondary" style={{ fontSize: 12 }}>
                请把临时密码发给该用户, 首次登录后建议立即修改。
                <Button
                  type="link" size="small" icon={<CopyOutlined />}
                  onClick={() => copy(createdPwd)}
                  style={{ padding: '0 4px' }}
                >
                  复制
                </Button>
              </Text>
            }
            data-testid="user-temp-password-alert"
          />
        )}

        <Form form={form} layout="vertical" requiredMark="optional">
          <Form.Item
            name="email" label="邮箱" rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '邮箱格式不正确' },
            ]}
          >
            <Input
              prefix={<MailOutlined />}
              placeholder="user@example.com"
              disabled={drawer.mode === 'edit'}
              data-testid="user-drawer-email"
            />
          </Form.Item>

          <Form.Item
            name="name" label="姓名" rules={[{ required: true, message: '请输入姓名' }]}
          >
            <Input prefix={<UserOutlined />} placeholder="张三" data-testid="user-drawer-name" />
          </Form.Item>

          <Form.Item
            name="role" label="角色" rules={[{ required: true, message: '请选择角色' }]}
            tooltip="管理员: 全部权限 / 编辑: 文档读写 / 只读: 仅查看"
          >
            <Select
              data-testid="user-drawer-role"
              options={[
                { label: <Tag color="red">管理员</Tag>, value: 'admin' },
                { label: <Tag color="blue">编辑</Tag>, value: 'editor' },
                { label: <Tag color="default">只读</Tag>, value: 'viewer' },
              ]}
            />
          </Form.Item>

          <Form.Item
            name="is_active" label="状态" valuePropName="checked"
            tooltip="禁用后该用户无法登录, 但保留其历史数据"
          >
            <Switch checkedChildren="启用" unCheckedChildren="禁用" data-testid="user-drawer-active" />
          </Form.Item>
        </Form>

        {drawer.mode === 'edit' && drawer.user && (
          <div style={{ marginTop: 16, padding: 12, background: 'var(--bg-tertiary, #f5f5f7)', borderRadius: 8 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              ID: {drawer.user.id}
            </Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              最后活跃: {fmtTime(drawer.user.last_login_at)}
            </Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              创建: {new Date(drawer.user.created_at).toLocaleString('zh-CN')}
            </Text>
          </div>
        )}
      </Drawer>
    </MainLayout>
  )
}
