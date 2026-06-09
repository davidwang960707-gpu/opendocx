/**
 * IndexDocEditor — 项目级首页配置编辑 (Phase 5 段 C 收官)
 *
 * Admin R12+: "管理员用 markdown 自由编辑首页 Hero, 不应该走 import_markdown 上传"
 *
 * 工作流:
 *  1. 父组件 (ProjectOverview) 找 default version 的 slug="index" doc
 *  2. 没找到 → 抽屉显示 "未找到 index doc" (异常态, 但正常 create_project 都自动建)
 *  3. 找到 → 抽屉显示编辑器 (左侧 markdown textarea, 右侧原始 markdown 提示)
 *  4. 顶部状态徽章 (draft / published) + 保存草稿 + 发布 + 取消发布 + 重新构建按钮
 *
 * 不需要新后端 API — 复用 documentApi.get / update + buildApi.trigger
 */
import { useEffect, useState } from 'react'
import {
  Drawer, Button, Space, Tag, Input, message, Spin, Alert, Tooltip, Empty, Typography,
} from 'antd'
import {
  EditOutlined, SaveOutlined, CloudUploadOutlined, ThunderboltOutlined,
  EyeOutlined, LinkOutlined,
} from '@ant-design/icons'
import { documentApi, buildApi } from '../services/api'

const { TextArea } = Input
const { Text } = Typography

export interface IndexDoc {
  id: string
  title: string
  slug: string
  content: string
  status: 'draft' | 'published' | 'archived'
  updated_at?: string
  version_id: string
}

export interface IndexDocEditorProps {
  open: boolean
  onClose: () => void
  /** 父组件已查到的 index doc (来自 GET /versions/{vid}/documents 过滤) */
  indexDoc: IndexDoc | null
  /** project + version 标识, 用于 "查看线上" 链接 */
  projectSlug: string
  versionLabel: string
  onSaved: (updated: IndexDoc) => void
}

export default function IndexDocEditor({
  open, onClose, indexDoc, projectSlug, versionLabel, onSaved,
}: IndexDocEditorProps) {
  const [content, setContent] = useState('')
  const [title, setTitle] = useState('')
  const [saving, setSaving] = useState(false)
  const [building, setBuilding] = useState(false)
  const [dirty, setDirty] = useState(false)

  // 抽屉打开 / indexDoc 变更 → 重置本地状态
  useEffect(() => {
    if (open && indexDoc) {
      setContent(indexDoc.content || '')
      setTitle(indexDoc.title || '')
      setDirty(false)
    }
  }, [open, indexDoc?.id])

  if (!indexDoc) {
    return (
      <Drawer
        open={open}
        onClose={onClose}
        title="首页配置"
        width={520}
      >
        <Empty
          description="未找到 slug=index 的首页配置文档"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        >
          <Text type="secondary" style={{ fontSize: 12 }}>
            create_project 会自动建; 若是早期项目, 可手动在管理后台建一个 slug=index 的草稿。
          </Text>
        </Empty>
      </Drawer>
    )
  }

  const isPublished = indexDoc.status === 'published'
  const previewUrl = `/docs/${projectSlug}/${versionLabel}/index.html`

  // 保存草稿 — content + status=draft
  const handleSaveDraft = async () => {
    if (saving) return
    setSaving(true)
    try {
      const r = await documentApi.update(indexDoc.id, {
        title,
        content,
        status: 'draft',
      })
      // axios 包装: r.data = ApiResponse { data, meta }
      // ApiResponse.data = Document
      const apiResp = (r as any).data
      const updated = apiResp?.data || apiResp || r
      message.success('已保存为草稿')
      setDirty(false)
      onSaved({
        ...indexDoc,
        title: updated.title ?? title,
        content: updated.content ?? content,
        status: 'draft',
        updated_at: updated.updated_at ?? new Date().toISOString(),
      })
    } catch (e: any) {
      message.error(`保存失败: ${e?.message ?? e}`)
    } finally {
      setSaving(false)
    }
  }

  // 发布 — status=published
  const handlePublish = async () => {
    if (saving) return
    setSaving(true)
    try {
      // 先 save content (用户可能改过), 再设 published
      await documentApi.update(indexDoc.id, { title, content })
      await documentApi.update(indexDoc.id, { status: 'published' })
      message.success('已发布 (重新构建后 Hero 内容会更新)')
      setDirty(false)
      onSaved({
        ...indexDoc,
        title,
        content,
        status: 'published',
        updated_at: new Date().toISOString(),
      })
    } catch (e: any) {
      message.error(`发布失败: ${e?.message ?? e}`)
    } finally {
      setSaving(false)
    }
  }

  // 取消发布 — status=draft
  const handleUnpublish = async () => {
    if (saving) return
    setSaving(true)
    try {
      await documentApi.update(indexDoc.id, { status: 'draft' })
      message.success('已取消发布 (Hero 回到默认 hardcode)')
      onSaved({ ...indexDoc, status: 'draft' })
    } catch (e: any) {
      message.error(`取消发布失败: ${e?.message ?? e}`)
    } finally {
      setSaving(false)
    }
  }

  // 触发构建
  const handleBuild = async () => {
    if (building) return
    setBuilding(true)
    try {
      const r = await buildApi.trigger(indexDoc.version_id)
      const apiResp = (r as any).data
      const data = apiResp?.data || apiResp || r
      message.success(`构建已触发: ${data?.id?.slice(0, 8) ?? ''} (${data?.status ?? 'pending'})`)
    } catch (e: any) {
      message.error(`构建失败: ${e?.message ?? e}`)
    } finally {
      setBuilding(false)
    }
  }

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={
        <Space>
          <EditOutlined style={{ color: 'var(--brand-primary, #4F46E5)' }} />
          <span>首页配置</span>
          <Tag color={isPublished ? 'green' : 'default'} style={{ marginLeft: 4 }}>
            {isPublished ? '已发布' : '草稿'}
          </Tag>
          {dirty && <Tag color="orange">未保存</Tag>}
        </Space>
      }
      width={1000}
      footer={
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space>
            <Tooltip title="在静态站打开首页 (当前 build)">
              <Button
                icon={<LinkOutlined />}
                onClick={() => window.open(previewUrl, '_blank')}
              >
                查看线上
              </Button>
            </Tooltip>
            <Tooltip title="重新触发构建, 让 Hero 内容生效">
              <Button
                icon={<ThunderboltOutlined />}
                loading={building}
                onClick={handleBuild}
              >
                重新构建
              </Button>
            </Tooltip>
          </Space>
          <Space>
            {isPublished && (
              <Button onClick={handleUnpublish} loading={saving} danger>
                取消发布
              </Button>
            )}
            <Button
              icon={<SaveOutlined />}
              loading={saving}
              onClick={handleSaveDraft}
            >
              保存草稿
            </Button>
            <Button
              type="primary"
              icon={<CloudUploadOutlined />}
              loading={saving}
              onClick={handlePublish}
            >
              {isPublished ? '更新发布' : '发布'}
            </Button>
          </Space>
        </Space>
      }
    >
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        {/* 提示 */}
        <Alert
          type="info"
          showIcon
          message="段 C 决策 B: 首页 Hero 整体由 slug=index 的文档驱动 (2026-06-05)"
          description={
            <span style={{ fontSize: 12 }}>
              编辑下方 markdown, <strong>H1 → hero 标题</strong>, <strong>第一段 P → hero 描述</strong>,
              其余 H2/H3 + 列表 + 代码块 + 表格 全部渲染到 hero 下方附加内容区。
              发布后点「重新构建」让 Hero 生效。
            </span>
          }
        />

        {/* 标题 */}
        <div>
          <div style={{ marginBottom: 6, fontSize: 12, color: 'var(--text-secondary, #666)' }}>
            标题 (H1 — 会被自动剥离, 留空也行)
          </div>
          <Input
            value={title}
            placeholder="例如: OpenDocX Demo"
            onChange={e => { setTitle(e.target.value); setDirty(true) }}
          />
        </div>

        {/* Markdown 编辑器 */}
        <div>
          <div style={{
            marginBottom: 6, fontSize: 12, color: 'var(--text-secondary, #666)',
            display: 'flex', justifyContent: 'space-between',
          }}>
            <span>Markdown 内容 (GFM 语法 — H2/H3/列表/代码块/表格)</span>
            <span>{content.length} 字符 · {content.split('\n').length} 行</span>
          </div>
          <TextArea
            value={content}
            onChange={e => { setContent(e.target.value); setDirty(true) }}
            autoSize={{ minRows: 18, maxRows: 32 }}
            placeholder={`# ${title || '项目名'}\n\n一段项目描述\n\n## 核心特性\n\n- 特性 1\n- 特性 2\n\n## 快速开始\n\n从「快速入门」开始, 5 分钟即可完成第一次构建。\n\n## 技术栈\n\n- 后端: FastAPI + SQLAlchemy 2.0 + pgvector\n- 前端: React + Vite + Ant Design`}
            style={{
              fontFamily: '"SF Mono", Menlo, Monaco, Consolas, monospace',
              fontSize: 13,
              lineHeight: 1.6,
            }}
            spellCheck={false}
          />
        </div>

        {/* 状态信息 */}
        <Alert
          type={isPublished ? 'success' : 'warning'}
          showIcon
          message={
            isPublished
              ? '已发布: Hero 当前显示此文档内容 (取决于最近一次 build)'
              : '草稿: Hero 仍显示默认 hardcode 内容, 需点击「发布」并「重新构建」'
          }
        />
      </Space>
    </Drawer>
  )
}
