/**
 * PreBuildModal — R15 预构建确认弹窗
 *
 * 触发: 用户点"构建"按钮
 * 行为:
 *  1. 展示 version 下所有 doc 的树形结构 (复用 R9 toTreeData 思路)
 *  2. 每行显示 [已发布 / 草稿 / 空内容] 状态徽章
 *  3. 顶部统计: N 个已发布 / M 个未发布 / K 个空内容
 *  4. 多选 checkbox (只 draft 可勾), 顶部"全选未发布"按钮
 *  5. (a) 单条"发布"按钮 (无未保存改动) — 调 documentApi.update
 *  6. (b) "保存+发布"按钮 (有未保存改动) — 调 documentApi.update + status
 *  7. 批量发布 (勾多个) — 调 documentApi.batchPublish
 *  8. 底部"开始构建"按钮 (主) — 真正调 buildApi.trigger
 *  9. 0 draft 时弹窗可省 (打开瞬间检测, 自动开始构建)
 *
 * 设计: Admin硬规则 v3 #1 (5min 默认 A), 复用 R13 AIFloatingActions 风格
 * 通信: 走 props.selectedDoc.content (前端编辑器状态) + props.onAfterPublish
 */

import { useEffect, useState, useMemo, useCallback } from 'react'
import { Modal, Button, Checkbox, Tree, Tag, Space, message, Spin, Alert } from 'antd'
import {
  RocketOutlined, CheckCircleOutlined, EditOutlined,
  FileTextOutlined, FolderOutlined, ExclamationCircleOutlined,
} from '@ant-design/icons'
import { documentApi, buildApi } from '../../services/api'
import type { DocumentTreeNode } from '../../types/api'

interface Props {
  open: boolean
  onClose: () => void
  /** 当前 version id (build 触发用) */
  versionId: string | null
  /** 当前 version 名 (显示用, 例 "v1.0") */
  versionName?: string
  /** 当前选中的 doc (用于检测未保存改动) */
  selectedDocId: string | null
  /** 当前选中的 doc 编辑器内容 (用于"保存+发布"二合一) */
  selectedDocEditingContent?: string
  /** 构建成功后回调 (父组件用来刷新 lastBuild) */
  onAfterBuild?: (buildResult: any) => void
  /** 父组件的 doc 树 (从 Documents.tsx 传进来) */
  docTree: DocumentTreeNode[]
  /** 重新拉 doc 树的回调 (发布后刷新) */
  onTreeRefresh?: () => void
}

interface FlatDoc {
  id: string
  title: string
  slug: string
  status: 'draft' | 'published' | 'archived'
  isFolder: boolean
  hasContent: boolean
  contentLen: number
  // 编辑器里有未保存改动的 doc
  dirty?: boolean
}

const STATUS_COLORS: Record<string, string> = {
  published: 'green',
  draft: 'orange',
  archived: 'default',
}

const STATUS_LABELS: Record<string, string> = {
  published: '已发布',
  draft: '草稿',
  archived: '已归档',
}

export default function PreBuildModal({
  open, onClose, versionId, versionName,
  selectedDocId, selectedDocEditingContent,
  onAfterBuild, docTree, onTreeRefresh,
}: Props) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [publishing, setPublishing] = useState(false)
  const [building, setBuilding] = useState(false)

  // 把树拍平成 flat 列表 (便于统计 / 排序 / 选择)
  const flat: FlatDoc[] = useMemo(() => {
    const out: FlatDoc[] = []
    const walk = (nodes: DocumentTreeNode[], dirtySet: Set<string>) => {
      for (const n of nodes) {
        out.push({
          id: n.id,
          title: n.title,
          slug: n.slug,
          status: (n.status as any) || 'draft',
          isFolder: n.is_folder ?? false,
          hasContent: n.has_content ?? false,
          contentLen: n.content_len ?? 0,
          dirty: dirtySet.has(n.id),
        })
        if (n.children?.length) walk(n.children, dirtySet)
      }
    }
    // 计算 dirty 集合: 当前编辑的 doc 跟已保存内容不一致
    const dirtySet = new Set<string>()
    if (selectedDocId && selectedDocEditingContent != null) {
      // 简单判断: 编辑器内容非空就当 dirty (父组件可传更精确的"已保存"对比)
      // 实际上 dirty 检测由父组件在做, 这里假设"selectedDocId + editingContent" 就代表 dirty
      dirtySet.add(selectedDocId)
    }
    walk(docTree, dirtySet)
    return out
  }, [docTree, selectedDocId, selectedDocEditingContent])

  // 统计
  const stats = useMemo(() => {
    const docs = flat.filter(d => !d.isFolder)
    const published = docs.filter(d => d.status === 'published').length
    const draft = docs.filter(d => d.status === 'draft' && d.hasContent).length
    const emptyDraft = docs.filter(d => d.status === 'draft' && !d.hasContent).length
    return { total: docs.length, published, draft, emptyDraft }
  }, [flat])

  // AntD Tree 用的 treeData (用 FlatDoc 转)
  const treeData = useMemo(() => {
    const toAntdNode = (nodes: DocumentTreeNode[]): any[] =>
      nodes.map(n => ({
        key: n.id,
        title: n.title,
        isLeaf: !(n.children?.length),
        children: n.children?.length ? toAntdNode(n.children) : undefined,
        // 状态 / checkbox 由 renderNode 控制
        raw: n,
      }))
    return toAntdNode(docTree)
  }, [docTree])

  // 切换 doc 选中
  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // 全选未发布
  const selectAllUnpublished = () => {
    const ids = flat.filter(d => d.status === 'draft' && d.hasContent).map(d => d.id)
    setSelectedIds(new Set(ids))
  }

  // 清空选择
  const clearSelection = () => setSelectedIds(new Set())

  // (a) 单条"发布" (无未保存改动)
  const publishOne = async (id: string) => {
    try {
      await documentApi.update(id, { status: 'published' })
      message.success('已发布')
      onTreeRefresh?.()
    } catch (e: any) {
      message.error(`发布失败: ${e.message}`)
    }
  }

  // (b) "保存+发布" (有未保存改动) - 当前选中的 doc
  const saveAndPublishCurrent = async () => {
    if (!selectedDocId || selectedDocEditingContent == null) return
    try {
      await documentApi.update(selectedDocId, {
        content: selectedDocEditingContent,
        status: 'published',
      })
      message.success('保存并发布成功')
      onTreeRefresh?.()
    } catch (e: any) {
      message.error(`保存+发布失败: ${e.message}`)
    }
  }

  // 批量发布 (勾选)
  const batchPublish = async () => {
    if (selectedIds.size === 0) {
      message.warning('请先勾选要发布的文档')
      return
    }
    setPublishing(true)
    try {
      const res = await documentApi.batchPublish(Array.from(selectedIds), true)
      const data = res.data.data
      message.success(
        `发布 ${data.published.length} 个 / 跳过 ${data.skipped.length} 个 / 失败 ${data.errors.length} 个`
      )
      setSelectedIds(new Set())
      onTreeRefresh?.()
    } catch (e: any) {
      message.error(`批量发布失败: ${e.message}`)
    } finally {
      setPublishing(false)
    }
  }

  // 开始构建
  const startBuild = async () => {
    if (!versionId) {
      message.error('versionId 不存在')
      return
    }
    setBuilding(true)
    try {
      const res = await buildApi.trigger(versionId)
      if (res.data.data.status === 'success') {
        message.success('构建成功')
        onAfterBuild?.(res.data.data)
        onClose()
      } else {
        message.error('构建失败, 请查看日志')
      }
    } catch (e: any) {
      message.error(`构建请求失败: ${e.message}`)
    } finally {
      setBuilding(false)
    }
  }

  // 0 draft 时直接开始构建 (Admin体验优化: 不打扰)
  // 但 Modal 仍然打开, 让Admin看到"啥也没做"的状态
  // 这里选择: 弹窗打开瞬间, 0 draft 时显示"全已发布"提示, 让Admin主动点"开始构建"
  // (Admin硬规则 v3: 不擅自代替用户点按钮)

  // Tree 节点渲染
  const renderTreeNode = (nodeData: any) => {
    const raw: DocumentTreeNode = nodeData.raw
    const isFolder = raw.is_folder ?? false
    const status = (raw.status as string) || 'draft'
    const hasContent = raw.has_content ?? false
    const isSelectedDoc = raw.id === selectedDocId
    const isChecked = selectedIds.has(raw.id)
    const canSelect = status === 'draft' && hasContent

    return (
      <div className="prebuild-tree-row" style={{
        display: 'flex', alignItems: 'center', gap: 8, width: '100%',
      }}>
        {/* folder / doc icon */}
        {isFolder ? <FolderOutlined style={{ color: '#999' }} /> : <FileTextOutlined style={{ color: '#5B7CFA' }} />}
        {/* checkbox (folder 不可选) */}
        {!isFolder && canSelect && (
          <Checkbox
            checked={isChecked}
            onChange={() => toggleSelect(raw.id)}
            onClick={(e) => e.stopPropagation()}
          />
        )}
        {!isFolder && !canSelect && (
          <span style={{ width: 16, display: 'inline-block' }} />  /* 占位对齐 */
        )}
        {/* title */}
        <span style={{
          flex: 1, minWidth: 0,
          color: isSelectedDoc ? '#5B7CFA' : undefined,
          fontWeight: isSelectedDoc ? 600 : 400,
        }}>
          {raw.title}
        </span>
        {/* 状态徽章 */}
        <Tag color={STATUS_COLORS[status] || 'default'}>
          {STATUS_LABELS[status] || status}
        </Tag>
        {/* folder-only (无内容) 提示 */}
        {!isFolder && !hasContent && (
          <Tag color="default" style={{ fontSize: 11 }}>空内容</Tag>
        )}
        {/* 当前选中 + draft + 有改动 → (b) 保存+发布 */}
        {isSelectedDoc && status === 'draft' && isFolder === false && (
          <Button
            size="small"
            type="link"
            onClick={(e) => { e.stopPropagation(); saveAndPublishCurrent() }}
          >
            保存+发布
          </Button>
        )}
        {/* (a) 单条发布 - 任意 draft 非当前选中 (无改动) */}
        {status === 'draft' && hasContent && !isSelectedDoc && (
          <Button
            size="small"
            type="link"
            onClick={(e) => { e.stopPropagation(); publishOne(raw.id) }}
          >
            发布
          </Button>
        )}
      </div>
    )
  }

  return (
    <Modal
      open={open}
      onCancel={onClose}
      title={
        <Space>
          <RocketOutlined />
          <span>预构建确认</span>
          <span style={{ color: '#999', fontSize: 13, fontWeight: 400 }}>
            {versionName || '未知版本'}
          </span>
        </Space>
      }
      width={720}
      footer={[
        <Button key="cancel" onClick={onClose}>取消</Button>,
        <Button
          key="build"
          type="primary"
          icon={<RocketOutlined />}
          loading={building}
          onClick={startBuild}
        >
          开始构建
        </Button>,
      ]}
    >
      {/* 顶部统计 */}
      <Alert
        type={stats.draft > 0 ? 'warning' : 'success'}
        showIcon
        message={
          <Space>
            <span>共 <strong>{stats.total}</strong> 个文档</span>
            <span>·</span>
            <span><CheckCircleOutlined style={{ color: '#52c41a' }} /> 已发布 <strong>{stats.published}</strong></span>
            <span>·</span>
            <span><EditOutlined style={{ color: '#faad14' }} /> 未发布 <strong>{stats.draft}</strong></span>
            {stats.emptyDraft > 0 && (
              <>
                <span>·</span>
                <span><ExclamationCircleOutlined style={{ color: '#999' }} /> 空内容 <strong>{stats.emptyDraft}</strong></span>
              </>
            )}
          </Space>
        }
        style={{ marginBottom: 16 }}
      />

      {/* 批量操作栏 */}
      {stats.draft > 0 && (
        <Space style={{ marginBottom: 12 }}>
          <Button size="small" onClick={selectAllUnpublished}>
            全选未发布 ({stats.draft})
          </Button>
          <Button size="small" onClick={clearSelection} disabled={selectedIds.size === 0}>
            清空选择
          </Button>
          <Button
            size="small"
            type="primary"
            loading={publishing}
            disabled={selectedIds.size === 0}
            onClick={batchPublish}
          >
            批量发布选中 ({selectedIds.size})
          </Button>
        </Space>
      )}

      {/* doc 树 */}
      <div style={{
        maxHeight: 400, overflowY: 'auto',
        border: '1px solid #f0f0f0', borderRadius: 4, padding: 8,
        background: '#fafafa',
      }}>
        {flat.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#999', padding: 32 }}>
            <Spin /> 加载中...
          </div>
        ) : (
          <Tree
            treeData={treeData}
            defaultExpandAll
            selectable={false}
            showLine
            blockNode
            titleRender={renderTreeNode}
          />
        )}
      </div>
    </Modal>
  )
}
