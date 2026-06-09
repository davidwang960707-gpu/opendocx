/**
 * VersionManageDrawer — 版本管理抽屉 (R6 反馈 2)
 *
 * 操作:
 *  - 新建版本
 *  - 设为默认
 *  - 归档
 *  - 查看状态
 */
import { useEffect, useState } from 'react'
import { Drawer, Button, Space, Tag, Input, Form, message, Popconfirm, List, Tooltip } from 'antd'
import { PlusOutlined, StarOutlined, StarFilled, InboxOutlined } from '@ant-design/icons'
import { versionApi } from '../services/api'

interface Props {
  open: boolean
  onClose: () => void
  projectId: string
  versions: any[]
  onChange: () => void
}

export default function VersionManageDrawer({ open, onClose, projectId, versions, onChange }: Props) {
  const [creating, setCreating] = useState(false)
  const [form] = Form.useForm()
  const [busy, setBusy] = useState<string | null>(null)

  useEffect(() => {
    if (!open) { form.resetFields(); setCreating(false) }
  }, [open, form])

  const handleCreate = async (values: { version: string }) => {
    try {
      const ver = values.version.trim()
      if (!ver) { message.error('版本号不能为空'); return }
      // 检查重名
      if (versions.some((v: any) => v.version === ver)) {
        message.error('版本号已存在')
        return
      }
      await versionApi.create(projectId, { version: ver, is_default: false })
      message.success(`版本 ${ver} 创建成功`)
      form.resetFields()
      setCreating(false)
      onChange()
    } catch (e: any) {
      message.error('创建失败: ' + (e?.response?.data?.detail || e?.message))
    }
  }

  const handleSetDefault = async (vid: string) => {
    setBusy(vid)
    try {
      await versionApi.setDefault(vid)
      message.success('已设为默认版本')
      onChange()
    } catch (e: any) {
      message.error('操作失败: ' + (e?.response?.data?.detail || e?.message))
    } finally {
      setBusy(null)
    }
  }

  const handleArchive = async (vid: string) => {
    setBusy(vid)
    try {
      await versionApi.archive(vid)
      message.success('已归档')
      onChange()
    } catch (e: any) {
      message.error('归档失败: ' + (e?.response?.data?.detail || e?.message))
    } finally {
      setBusy(null)
    }
  }

  return (
    <Drawer
      title="版本管理"
      placement="right"
      width={420}
      open={open}
      onClose={onClose}
      extra={
        <Button
          type="primary"
          size="small"
          icon={<PlusOutlined />}
          onClick={() => setCreating(c => !c)}
        >
          新建版本
        </Button>
      }
    >
      {creating && (
        <Form form={form} layout="inline" onFinish={handleCreate} style={{ marginBottom: 16 }}>
          <Form.Item name="version" rules={[{ required: true, message: '必填' }]} style={{ flex: 1, marginRight: 8 }}>
            <Input placeholder="v1.2.0" autoFocus />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" size="small">创建</Button>
              <Button size="small" onClick={() => { setCreating(false); form.resetFields() }}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      )}

      <List
        size="small"
        dataSource={versions}
        locale={{ emptyText: '暂无版本' }}
        renderItem={(v: any) => (
          <List.Item
            actions={[
              v.is_default ? (
                <Tag color="gold" icon={<StarFilled />} key="default">默认</Tag>
              ) : (
                <Tooltip title="设为默认" key="set">
                  <Button
                    type="text"
                    size="small"
                    icon={<StarOutlined />}
                    loading={busy === v.id}
                    onClick={() => handleSetDefault(v.id)}
                  />
                </Tooltip>
              ),
              v.status === 'archived' ? (
                <Tag key="archived">已归档</Tag>
              ) : v.is_default ? null : (
                <Popconfirm
                  key="archive"
                  title="归档此版本?"
                  description="归档后默认状态会取消, 可在历史中查看"
                  onConfirm={() => handleArchive(v.id)}
                  okText="归档"
                  cancelText="取消"
                >
                  <Tooltip title="归档">
                    <Button
                      type="text"
                      size="small"
                      icon={<InboxOutlined />}
                      loading={busy === v.id}
                      danger
                    />
                  </Tooltip>
                </Popconfirm>
              ),
            ].filter(Boolean)}
          >
            <List.Item.Meta
              title={
                <Space>
                  <span style={{ fontWeight: 500 }}>{v.version}</span>
                  {v.is_default && <Tag color="gold" style={{ marginLeft: 0 }}>默认</Tag>}
                  {v.status === 'archived' && <Tag>已归档</Tag>}
                </Space>
              }
              description={new Date(v.created_at).toLocaleString('zh-CN')}
            />
          </List.Item>
        )}
      />
    </Drawer>
  )
}
