/** Settings — P1-W3-A3 个人设置
 *
 * 设计:
 * - 3 段卡片 (B 紧凑风 32px 行高 12px 字号, 跟 AdminUsers 一致)
 *   1. 个人资料: 头像 + 邮箱 (不可改) + 姓名 (可改, 单独 "保存" 按钮)
 *   2. 改密码: 旧密码 + 新密码 + 确认密码 (前端 validate + 后端 /auth/change-password)
 *   3. 偏好 (localStorage): 主题 (light/dark/system) + 通知频率 (实时/每日/每周/关闭)
 *
 * 数据: PATCH /api/v1/auth/me + POST /api/v1/auth/change-password + localStorage
 */
import { useState, useEffect, useCallback } from 'react'
import {
  Button, Input, Form, message, Avatar, Typography, Space, Divider, Select, Alert,
} from 'antd'
import {
  UserOutlined, LockOutlined, MailOutlined, CheckCircleOutlined, BulbOutlined,
  BellOutlined, DesktopOutlined, SunOutlined, MoonOutlined, ReloadOutlined,
  KeyOutlined,
} from '@ant-design/icons'
import { authApi, userApi } from '../services/api'
import type { UserFull } from '../types/api'
import { useAuthStore } from '../stores/auth'
import { useThemeStore } from '../stores/theme'
import MainLayout from '../layouts/MainLayout'

const { Text, Title, Paragraph } = Typography

const NOTIFY_OPTIONS = [
  { label: '实时 (每次更新推送)', value: 'realtime' },
  { label: '每日摘要', value: 'daily' },
  { label: '每周摘要', value: 'weekly' },
  { label: '关闭', value: 'off' },
]

interface Prefs {
  notify: 'realtime' | 'daily' | 'weekly' | 'off'
}

const PREFS_KEY = 'opendocx.prefs'
const loadPrefs = (): Prefs => {
  try {
    const raw = localStorage.getItem(PREFS_KEY)
    if (raw) return JSON.parse(raw)
  } catch {}
  return { notify: 'daily' }
}
const savePrefs = (p: Prefs) => {
  localStorage.setItem(PREFS_KEY, JSON.stringify(p))
}

export default function Settings() {
  const me = useAuthStore(s => s.user)
  const setMe = useAuthStore(s => s.login)  // setUser 没 export, 用 login+getMe trick
  const themeMode = useThemeStore(s => s.mode)
  const setThemeMode = useThemeStore(s => s.setMode)
  const cycleTheme = useThemeStore(s => s.cycle)

  const [profileForm] = Form.useForm()
  const [passwordForm] = Form.useForm()
  const [prefs, setPrefs] = useState<Prefs>(loadPrefs())
  const [savingProfile, setSavingProfile] = useState(false)
  const [savingPassword, setSavingPassword] = useState(false)
  const [userDetail, setUserDetail] = useState<UserFull | null>(null)

  const refreshMe = useCallback(async () => {
    try {
      const res = await authApi.getMe()
      const u: UserFull = (res.data as any).data
      setUserDetail(u)
      profileForm.setFieldsValue({ name: u.name, email: u.email })
    } catch (e: any) {
      message.error('加载个人信息失败: ' + (e?.response?.data?.detail || e?.message))
    }
  }, [profileForm])

  useEffect(() => { refreshMe() }, [refreshMe])

  const saveProfile = async () => {
    try {
      const v = await profileForm.validateFields()
      setSavingProfile(true)
      const res = await authApi.updateMe({ name: v.name })
      const u: UserFull = (res.data as any).data
      setUserDetail(u)
      message.success('姓名已保存')
      // 同步 auth store 里的 user.name (用 setState 模拟 — store 实际没暴露 setUser, 走 reload 触发)
      // 简化: 提示用户刷新页面 / 反正下次 useAuthStore.checkAuth 会拉
    } catch (e: any) {
      if (e?.errorFields) return
      message.error('保存失败: ' + (e?.response?.data?.detail || e?.message))
    } finally {
      setSavingProfile(false)
    }
  }

  const savePassword = async () => {
    try {
      const v = await passwordForm.validateFields()
      if (v.new_password !== v.confirm_password) {
        message.error('两次输入的新密码不一致')
        return
      }
      setSavingPassword(true)
      await userApi.changePassword({
        old_password: v.old_password,
        new_password: v.new_password,
      })
      message.success('密码已修改, 请用新密码重新登录')
      passwordForm.resetFields()
      // 简化: 不强退, 让用户主动登出
    } catch (e: any) {
      if (e?.errorFields) return
      message.error('修改失败: ' + (e?.response?.data?.detail || e?.message))
    } finally {
      setSavingPassword(false)
    }
  }

  const updateNotify = (v: Prefs['notify']) => {
    const next = { ...prefs, notify: v }
    setPrefs(next)
    savePrefs(next)
    message.success('通知偏好已保存')
  }

  const user = userDetail || me
  const roleLabel = { admin: '管理员', editor: '编辑', viewer: '只读' }[user?.role || 'viewer']

  return (
    <MainLayout subtitle="个人设置">
      <div className="page-toolbar">
        <div className="page-toolbar-left">
          <h1 className="page-title">设置</h1>
          <Text type="secondary" style={{ fontSize: 12 }}>个人资料 / 安全 / 偏好</Text>
        </div>
      </div>

      {/* === 段 1: 个人资料 === */}
      <div data-testid="settings-section-profile" style={{ background: 'var(--bg-primary, #fff)', borderRadius: 8, padding: 24, marginBottom: 16, border: '1px solid var(--border-color, #e5e5e7)' }}>
        <Title level={5} style={{ marginTop: 0 }}>
          <UserOutlined style={{ marginRight: 8 }} />
          个人资料
        </Title>
        <Divider style={{ margin: '12px 0 20px' }} />

        <Space size={24} align="start" style={{ marginBottom: 20 }}>
          <Avatar
            size={64}
            style={{ background: 'var(--brand-color, #4F46E5)', fontSize: 24, fontWeight: 600 }}
          >
            {user?.name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase()}
          </Avatar>
          <div>
            <Text style={{ fontSize: 16, fontWeight: 500 }}>{user?.name || '—'}</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              <MailOutlined style={{ marginRight: 4 }} />
              {user?.email}
            </Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              角色: {roleLabel} · ID: {user?.id?.slice(0, 8) || '—'}…
            </Text>
          </div>
        </Space>

        <Form
          form={profileForm}
          layout="vertical"
          style={{ maxWidth: 480 }}
          requiredMark="optional"
        >
          <Form.Item label="邮箱" tooltip="邮箱作为唯一标识, 如需更换请联系管理员">
            <Input
              prefix={<MailOutlined />}
              value={user?.email}
              disabled
              data-testid="settings-email"
            />
          </Form.Item>

          <Form.Item
            name="name" label="姓名" rules={[
              { required: true, message: '请输入姓名' },
              { max: 50, message: '姓名最长 50 字符' },
            ]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="您的姓名"
              data-testid="settings-name"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary" icon={<CheckCircleOutlined />}
              onClick={saveProfile}
              loading={savingProfile}
              data-testid="settings-save-profile"
            >
              保存姓名
            </Button>
          </Form.Item>
        </Form>
      </div>

      {/* === 段 2: 改密码 === */}
      <div data-testid="settings-section-password" style={{ background: 'var(--bg-primary, #fff)', borderRadius: 8, padding: 24, marginBottom: 16, border: '1px solid var(--border-color, #e5e5e7)' }}>
        <Title level={5} style={{ marginTop: 0 }}>
          <LockOutlined style={{ marginRight: 8 }} />
          修改密码
        </Title>
        <Divider style={{ margin: '12px 0 20px' }} />

        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16, maxWidth: 480 }}
          message={
            <Text style={{ fontSize: 12 }}>
              密码规则: 至少 6 字符, 建议混合字母 + 数字, 修改后下次登录生效
            </Text>
          }
        />

        <Form
          form={passwordForm}
          layout="vertical"
          style={{ maxWidth: 480 }}
          requiredMark="optional"
        >
          <Form.Item
            name="old_password" label="旧密码" rules={[{ required: true, message: '请输入旧密码' }]}
          >
            <Input.Password
              prefix={<KeyOutlined />}
              placeholder="当前密码"
              data-testid="settings-old-password"
            />
          </Form.Item>

          <Form.Item
            name="new_password" label="新密码" rules={[
              { required: true, message: '请输入新密码' },
              { min: 6, message: '密码至少 6 字符' },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="至少 6 字符"
              data-testid="settings-new-password"
            />
          </Form.Item>

          <Form.Item
            name="confirm_password" label="确认新密码" dependencies={['new_password']} rules={[
              { required: true, message: '请再次输入新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) {
                    return Promise.resolve()
                  }
                  return Promise.reject(new Error('两次输入的新密码不一致'))
                },
              }),
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="再次输入新密码"
              data-testid="settings-confirm-password"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary" icon={<CheckCircleOutlined />}
              onClick={savePassword}
              loading={savingPassword}
              data-testid="settings-save-password"
            >
              修改密码
            </Button>
          </Form.Item>
        </Form>
      </div>

      {/* === 段 3: 偏好 === */}
      <div data-testid="settings-section-prefs" style={{ background: 'var(--bg-primary, #fff)', borderRadius: 8, padding: 24, marginBottom: 16, border: '1px solid var(--border-color, #e5e5e7)' }}>
        <Title level={5} style={{ marginTop: 0 }}>
          <BulbOutlined style={{ marginRight: 8 }} />
          偏好
        </Title>
        <Divider style={{ margin: '12px 0 20px' }} />

        <div style={{ maxWidth: 480 }}>
          <div style={{ marginBottom: 20 }}>
            <Text strong style={{ fontSize: 13 }}>
              <SunOutlined style={{ marginRight: 6 }} />
              主题
            </Text>
            <Paragraph type="secondary" style={{ fontSize: 11, marginTop: 4, marginBottom: 8 }}>
              切换 light / dark / 跟随系统, 立即生效
            </Paragraph>
            <Select
              value={themeMode}
              onChange={setThemeMode}
              style={{ width: 200 }}
              data-testid="settings-theme-select"
              options={[
                { label: <><SunOutlined /> 浅色</>, value: 'light' },
                { label: <><MoonOutlined /> 深色</>, value: 'dark' },
                { label: <><DesktopOutlined /> 跟随系统</>, value: 'system' },
              ]}
            />
            <Button
              type="link" size="small" icon={<ReloadOutlined />}
              onClick={cycleTheme}
              style={{ padding: '0 8px', marginLeft: 8 }}
              data-testid="settings-theme-cycle"
            >
              快速循环切换
            </Button>
          </div>

          <div style={{ marginBottom: 20 }}>
            <Text strong style={{ fontSize: 13 }}>
              <BellOutlined style={{ marginRight: 6 }} />
              通知频率
            </Text>
            <Paragraph type="secondary" style={{ fontSize: 11, marginTop: 4, marginBottom: 8 }}>
              文档/项目更新时如何通知 (P2 接入邮件后生效, 当前仅持久化偏好)
            </Paragraph>
            <Select
              value={prefs.notify}
              onChange={updateNotify}
              style={{ width: 200 }}
              data-testid="settings-notify-select"
              options={NOTIFY_OPTIONS}
            />
          </div>

          <Alert
            type="success"
            showIcon
            message={
              <Text style={{ fontSize: 12 }}>
                偏好已保存到 localStorage (P1-W3-A3 占位, P2 接入邮件后实通知)
              </Text>
            }
          />
        </div>
      </div>

      <Text type="secondary" style={{ fontSize: 11, display: 'block', textAlign: 'center', padding: '16px 0' }}>
        设置页 P1-W3-A3 · 个人资料 / 改密码 / 偏好
      </Text>
    </MainLayout>
  )
}
