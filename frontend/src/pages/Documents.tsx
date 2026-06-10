import { useEffect, useState, useCallback, useRef, useMemo } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { Typography, Button, Tree, Modal, Form, Input, message, Space, Select, Spin, Tag, Tooltip, Dropdown, Drawer, Popconfirm, Segmented, Breadcrumb, TreeSelect, Alert } from 'antd'
import {
  FileTextOutlined, PlusOutlined, FolderOutlined, FolderAddOutlined,
  ArrowLeftOutlined, SaveOutlined,
  EyeOutlined, RocketOutlined, DeleteOutlined, MessageOutlined, HistoryOutlined,
  EditOutlined, CompressOutlined, InboxOutlined,
  DoubleRightOutlined, DoubleLeftOutlined, MoreOutlined, RobotOutlined,
  SettingOutlined, StarOutlined, StarFilled, InboxOutlined as ArchiveIcon,
  FolderOpenOutlined,
} from '@ant-design/icons'
import MDEditor from '@uiw/react-md-editor'
import EditorAIPanel from '../components/Editor/EditorAIPanel'
import AIFloatingActions from '../components/Editor/AIFloatingActions'
import PreBuildModal from '../components/Editor/PreBuildModal'
import StatusBar from '../components/Editor/StatusBar'
import MarkdownUploader from '../components/Editor/MarkdownUploader'
import AppSider from '../components/AppSider'
import VersionManageDrawer from '../components/VersionManageDrawer'
import FolderOverview from '../components/FolderOverview'
import StatusBadges from '../components/StatusBadges'
import { useRegisterCommands } from '../App'
import { projectApi, versionApi, documentApi, buildApi } from '../services/api'
import type { DocumentTreeNode, DocumentCreateRequest } from '../types/api'
import ProjectOverview from './ProjectOverview'

const { Text } = Typography
const { TextArea } = Input

type ConflictState = {
  documentId: string
  docTitle: string
  baseRevision: number | null
  latestRevision: number
  latestContent: string
  draftContent: string
  latestUpdatedAt?: string | null
}

function buildDiffRows(left: string, right: string) {
  const leftLines = left.split('\n')
  const rightLines = right.split('\n')
  const max = Math.max(leftLines.length, rightLines.length)
  return Array.from({ length: max }, (_, i) => {
    const server = leftLines[i] ?? ''
    const draft = rightLines[i] ?? ''
    return {
      line: i + 1,
      server,
      draft,
      changed: server !== draft,
      onlyServer: i >= rightLines.length,
      onlyDraft: i >= leftLines.length,
    }
  })
}

export default function Documents() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  const [project, setProject] = useState<any>(null)
  const [versions, setVersions] = useState<any[]>([])
  const [currentVersion, setCurrentVersion] = useState<string>('')
  const [docTree, setDocTree] = useState<DocumentTreeNode[]>([])
  // Admin R13: build logs 数组 (embedded ProjectOverview 需要 构建次数 + 最近构建时间)
  const [builds, setBuilds] = useState<any[]>([])
  // R15: 预构建弹窗开关
  const [preBuildOpen, setPreBuildOpen] = useState(false)
  const [selectedDoc, setSelectedDoc] = useState<any>(null)
  const [selectedFolder, setSelectedFolder] = useState<DocumentTreeNode | null>(null)
  const [editingContent, setEditingContent] = useState('')
  const [savedContent, setSavedContent] = useState('')
  const [docRevision, setDocRevision] = useState<number | null>(null)
  const [conflict, setConflict] = useState<ConflictState | null>(null)
  const [mergeContent, setMergeContent] = useState('')
  const [lastSavedAt, setLastSavedAt] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [building, setBuilding] = useState(false)
  const [buildSuccessPulse, setBuildSuccessPulse] = useState(false)
  const [saveSuccessPulse, setSaveSuccessPulse] = useState(false)
  const [treePulse, setTreePulse] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [createParentId, setCreateParentId] = useState<string | null>(null)
  const [moveModalOpen, setMoveModalOpen] = useState(false)
  const [movingNode, setMovingNode] = useState<DocumentTreeNode | null>(null)
  const [moveTargetId, setMoveTargetId] = useState<string | null>(null)
  // P1-UI-折叠: AI 面板收折状态 (默认展开, 持久化到 localStorage)
  const [aiCollapsed, setAiCollapsed] = useState<boolean>(() => {
    try { return localStorage.getItem('docs.aiCollapsed') === '1' } catch { return false }
  })
  // R6 反馈 2: 版本管理抽屉
  const [versionDrawerOpen, setVersionDrawerOpen] = useState(false)
  useEffect(() => { try { localStorage.setItem('docs.aiCollapsed', aiCollapsed ? '1' : '0') } catch {} }, [aiCollapsed])
  // Tree 默认展开所有父节点
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([])
  // Admin需求 6-3: 4 段状态徽章
  const [lastBuild, setLastBuild] = useState<{ version: string; at: string } | null>(null)
  const [form] = Form.useForm()
  const editorContainerRef = useRef<HTMLDivElement>(null)
  const savePulseTimerRef = useRef<number | null>(null)
  const buildPulseTimerRef = useRef<number | null>(null)
  const treePulseTimerRef = useRef<number | null>(null)
  // 引用 MarkdownUploader 的 trigger button — 点 Tree header inbox 时手动打开
  const uploaderRef = useRef<any>(null)
  const conflictRows = useMemo(
    () => conflict ? buildDiffRows(conflict.latestContent, conflict.draftContent) : [],
    [conflict],
  )

  useEffect(() => {
    return () => {
      if (savePulseTimerRef.current) window.clearTimeout(savePulseTimerRef.current)
      if (buildPulseTimerRef.current) window.clearTimeout(buildPulseTimerRef.current)
      if (treePulseTimerRef.current) window.clearTimeout(treePulseTimerRef.current)
    }
  }, [])

  // ⌘K 面板注册本页命令
  useRegisterCommands('documents', [
    {
      id: 'doc.save', label: '保存当前文档', group: '文档',
      keywords: ['save', '保存', 'ctrl+s', '⌘s'],
      icon: <SaveOutlined />, shortcut: '⌘S',
      run: () => { if (selectedDoc) handleSave() },
    },
    {
      id: 'doc.publish', label: '发布当前文档', group: '文档',
      keywords: ['publish', '发布'],
      icon: <EyeOutlined />,
      run: () => { if (selectedDoc) handlePublish() },
    },
    {
      id: 'doc.build', label: '触发构建', group: '文档',
      keywords: ['build', '构建', '部署'],
      icon: <RocketOutlined />,
      run: () => { if (currentVersion) handleBuild() },
    },
    {
      id: 'doc.create', label: '新建文档', group: '文档',
      keywords: ['create', '新建', 'add'],
      icon: <PlusOutlined />, shortcut: '⌘N',
      run: () => setModalOpen(true),
    },
    {
      id: 'doc.upload', label: '上传 Markdown 文档', group: '文档',
      keywords: ['upload', '上传', 'import', 'md', 'markdown'],
      icon: <RocketOutlined />,
      run: () => { message.info('点击左栏上方"上传 .md"按钮') },
    },
    {
      id: 'ai.continue', label: 'AI 续写（光标处）', group: 'AI',
      keywords: ['ai', '续写', 'continue'],
      icon: <EditOutlined />,
      run: () => { message.info('请选中内容后用 AI 浮层触发') },
    },
    {
      id: 'ai.summarize', label: 'AI 总结当前文档', group: 'AI',
      keywords: ['ai', '总结', 'summarize'],
      icon: <CompressOutlined />,
      run: () => { message.info('请用 AI 浮层 / AI 面板触发（需选区）') },
    },
  ])

  useEffect(() => {
    if (!projectId) return
    projectApi.get(projectId).then(res => setProject(res.data.data))
    versionApi.list(projectId).then(res => {
      const vers = res.data.data || []
      setVersions(vers)
      const defaultVer = vers.find((v: any) => v.is_default) || vers[0]
      if (defaultVer) setCurrentVersion(defaultVer.id)
    })
    // Admin R13: 拉 build logs 数组 (embedded ProjectOverview 用)
    buildApi.logs(projectId).then(res => setBuilds(res.data.data || [])).catch(() => setBuilds([]))
  }, [projectId])

  const loadDocTree = useCallback(async () => {
    if (!currentVersion) return
    setLoading(true)
    try {
      const res = await documentApi.tree(currentVersion)
      const tree = res.data.data || []
      setDocTree(tree)
      // R6 反馈 4: 刷新后自动展开所有 root
      const collectKeys = (nodes: DocumentTreeNode[]): string[] => {
        const out: string[] = []
        const walk = (ns: DocumentTreeNode[]) => ns.forEach(n => {
          out.push(n.id)
          if (n.children?.length) walk(n.children)
        })
        walk(nodes)
        return out
      }
      setExpandedKeys(collectKeys(tree))
    } catch (err: any) {
      message.error('加载文档树失败: ' + (err?.response?.data?.detail || err?.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }, [currentVersion])

  useEffect(() => { loadDocTree() }, [loadDocTree])

  const pulseTree = useCallback(() => {
    setTreePulse(true)
    if (treePulseTimerRef.current) window.clearTimeout(treePulseTimerRef.current)
    treePulseTimerRef.current = window.setTimeout(() => setTreePulse(false), 1200)
  }, [])

  const refreshTreeWithPulse = useCallback(async () => {
    await loadDocTree()
    pulseTree()
  }, [loadDocTree, pulseTree])

  // Admin需求 6-3: 4 段状态徽章 — 拉最近一次构建
  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    ;(async () => {
      try {
        const res = await buildApi.latest(projectId, currentVersion || undefined)
        if (cancelled) return
        const b = res.data?.data
        if (b && b.status === 'success') {
          setLastBuild({ version: versions.find(v => v.id === currentVersion)?.version || 'v?', at: b.created_at })
        } else {
          setLastBuild(null)
        }
      } catch { setLastBuild(null) }
    })()
    return () => { cancelled = true }
  }, [projectId, currentVersion, versions])

  const handleSelectDoc = async (docId: string) => {
    // 先在 docTree 里找: 是 folder 还是 doc
    const findNode = (nodes: DocumentTreeNode[]): DocumentTreeNode | null => {
      for (const n of nodes) {
        if (n.id === docId) return n
        const r = findNode(n.children || [])
        if (r) return r
      }
      return null
    }
    const node = findNode(docTree)
    if (!node) return
    if (node.is_folder) {
      // folder: 设 selectedFolder, 清 selectedDoc 编辑态
      setSelectedFolder(node)
      setSelectedDoc(null)
      setDocRevision(null)
      return
    }
    // 文档: 走原逻辑
    setSelectedFolder(null)
    const res = await documentApi.get(docId)
    const doc = res.data.data
    setSelectedDoc(doc)
    const content = doc.content || ''
    setEditingContent(content)
    setSavedContent(content)
    setDocRevision(doc.revision ?? 1)
    setLastSavedAt(doc.updated_at ? new Date(doc.updated_at).getTime() : Date.now())
  }

  const openConflictModal = useCallback((err: any, draftContent: string) => {
    const detail = err?.response?.data?.detail
    if (err?.response?.status !== 409 || detail?.code !== 'document_conflict') return false
    const nextConflict: ConflictState = {
      documentId: detail.document_id || selectedDoc?.id,
      docTitle: selectedDoc?.title || '当前文档',
      baseRevision: detail.base_revision ?? docRevision,
      latestRevision: detail.latest_revision ?? 1,
      latestContent: detail.latest_content ?? '',
      draftContent: detail.draft_content ?? draftContent,
      latestUpdatedAt: detail.latest_updated_at,
    }
    setConflict(nextConflict)
    setMergeContent(nextConflict.draftContent)
    message.warning('文档已被其他人保存, 请对比差异后合并')
    return true
  }, [docRevision, selectedDoc])

  const applySavedDocument = useCallback((updated: any, fallbackContent: string) => {
    const content = updated?.content ?? fallbackContent
    setSelectedDoc(updated)
    setEditingContent(content)
    setSavedContent(content)
    setDocRevision(updated?.revision ?? null)
    setLastSavedAt(updated?.updated_at ? new Date(updated.updated_at).getTime() : Date.now())
    setSaveSuccessPulse(true)
    if (savePulseTimerRef.current) window.clearTimeout(savePulseTimerRef.current)
    savePulseTimerRef.current = window.setTimeout(() => setSaveSuccessPulse(false), 1600)
  }, [])

  const handleSave = async () => {
    if (!selectedDoc) return
    setSaving(true)
    try {
      const res = await documentApi.update(selectedDoc.id, {
        content: editingContent,
        base_revision: docRevision ?? undefined,
      })
      applySavedDocument(res.data.data, editingContent)
      message.success('保存成功')
    } catch (err: any) {
      if (!openConflictModal(err, editingContent)) {
        message.error('保存失败')
      }
    } finally {
      setSaving(false)
    }
  }

  const handleSaveMergedConflict = async () => {
    if (!conflict) return
    setSaving(true)
    try {
      const res = await documentApi.update(conflict.documentId, {
        content: mergeContent,
        base_revision: conflict.latestRevision,
      })
      applySavedDocument(res.data.data, mergeContent)
      setConflict(null)
      message.success('已保存合并结果')
    } catch (err: any) {
      if (!openConflictModal(err, mergeContent)) {
        message.error('合并保存失败')
      }
    } finally {
      setSaving(false)
    }
  }

  const handleUseServerVersion = () => {
    if (!conflict) return
    setEditingContent(conflict.latestContent)
    setSavedContent(conflict.latestContent)
    setDocRevision(conflict.latestRevision)
    setSelectedDoc((doc: any) => doc ? {
      ...doc,
      content: conflict.latestContent,
      revision: conflict.latestRevision,
      updated_at: conflict.latestUpdatedAt || doc.updated_at,
    } : doc)
    setLastSavedAt(conflict.latestUpdatedAt ? new Date(conflict.latestUpdatedAt).getTime() : Date.now())
    setConflict(null)
    message.info('已载入服务器最新版本')
  }

  const handleSaveConflictCopy = async () => {
    if (!conflict || !selectedDoc || !currentVersion) return
    setSaving(true)
    try {
      const suffix = Date.now().toString(36)
      const res = await documentApi.create(currentVersion, {
        title: `${selectedDoc.title}（冲突副本）`,
        slug: `${selectedDoc.slug}-conflict-${suffix}`,
        content: conflict.draftContent,
        parent_id: selectedDoc.parent_id || undefined,
        sort_order: (selectedDoc.sort_order || 0) + 1,
      })
      const copy = res.data.data
      setConflict(null)
      setSelectedFolder(null)
      setSelectedDoc(copy)
      setEditingContent(copy.content || '')
      setSavedContent(copy.content || '')
      setDocRevision(copy.revision ?? 1)
      setLastSavedAt(copy.updated_at ? new Date(copy.updated_at).getTime() : Date.now())
      await refreshTreeWithPulse()
      message.success('已保存为副本文档')
    } catch (err: any) {
      message.error(`保存副本失败: ${err?.response?.data?.detail || err?.message || '未知错误'}`)
    } finally {
      setSaving(false)
    }
  }

  const handlePublish = async () => {
    if (!selectedDoc) return
    const res = await documentApi.update(selectedDoc.id, { status: 'published' })
    message.success('已发布')
    // 刷新 selectedDoc 让 StatusBadges 立刻反映 status 变化
    setSelectedDoc(res.data.data)
    setDocRevision(res.data.data?.revision ?? docRevision)
    loadDocTree()
  }

  const handleCreateDoc = async (values: any) => {
    if (!currentVersion) return
    // Admin R8 反馈: 重名 doc 会 500
    // 防御: 自动给 slug 加 -2 / -3 ... 后缀避免冲突, 命中已有就累加
    const baseSlug = (values.slug && values.slug.trim())
      || values.title.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')
      || 'untitled'
    const existingSlugs = new Set<string>(
      (function collect(nodes: DocumentTreeNode[]): string[] {
        const out: string[] = []
        const walk = (ns: DocumentTreeNode[]) => ns.forEach(n => {
          out.push(n.slug)
          if (n.children?.length) walk(n.children)
        })
        walk(nodes)
        return out
      })(docTree)
    )
    let slug = baseSlug
    let suffix = 2
    while (existingSlugs.has(slug)) {
      slug = `${baseSlug}-${suffix}`
      suffix++
    }
    const req: DocumentCreateRequest = {
      title: values.title,
      slug,
      content: values.isFolder ? '' : `# ${values.title}\n\n`,
      parent_id: createParentId || undefined,
      sort_order: docTree.length + 1,
    }
    try {
      await documentApi.create(currentVersion, req as any)
      message.success(values.isFolder ? `文件夹「${values.title}」已创建` : `文档「${values.title}」已创建`)
      form.resetFields()
      setCreateParentId(null)
      await refreshTreeWithPulse()
      setModalOpen(false)
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      message.error('创建失败: ' + (detail || err?.message || '未知错误'))
    }
  }

  // R6 反馈 5: 拖拽排序 — 客户端把整棵树新位置打平
  // AntD Tree onDrop(info): info.node.key=dropped-onto, info.dragNode.key=dragged, info.dropPosition=-1=before, 0=inner, 1=after
  const flattenForReorder = (nodes: DocumentTreeNode[], parentId: string | null = null): { id: string; parent_id: string | null; sort_order: number }[] => {
    const out: { id: string; parent_id: string | null; sort_order: number }[] = []
    nodes.forEach((n, idx) => {
      out.push({ id: n.id, parent_id: parentId, sort_order: idx })
      if (n.children?.length) out.push(...flattenForReorder(n.children, n.id))
    })
    return out
  }

  const findNodeInTree = (nodes: DocumentTreeNode[], id: string): DocumentTreeNode | null => {
    for (const node of nodes) {
      if (node.id === id) return node
      const found = findNodeInTree(node.children || [], id)
      if (found) return found
    }
    return null
  }

  const isAncestorNode = (root: DocumentTreeNode, id: string): boolean => {
    if (root.id === id) return true
    return (root.children || []).some(child => isAncestorNode(child, id))
  }

  const removeNodeFromTree = (nodes: DocumentTreeNode[], id: string): DocumentTreeNode | null => {
    for (let i = 0; i < nodes.length; i++) {
      if (nodes[i].id === id) return nodes.splice(i, 1)[0]
      const removed = removeNodeFromTree(nodes[i].children || [], id)
      if (removed) return removed
    }
    return null
  }

  const getSelectedTreeNode = () => {
    const selectedId = selectedDoc?.id || selectedFolder?.id
    return selectedId ? findNodeInTree(docTree, selectedId) : null
  }

  const openMoveModal = (node: DocumentTreeNode | null) => {
    if (!node) {
      message.info('请先选择一个文档或文件夹')
      return
    }
    setMovingNode(node)
    setMoveTargetId(null)
    setMoveModalOpen(true)
  }

  const folderTreeOptions = useMemo(() => {
    const toOptions = (nodes: DocumentTreeNode[]): any[] => nodes.flatMap((node) => {
      const hasChildren = !!node.children?.length
      const isFolder = node.is_folder ?? hasChildren
      if (movingNode && isAncestorNode(movingNode, node.id)) return []
      const children = toOptions(node.children || [])
      if (!isFolder) return children
      return [{
        title: node.title,
        value: node.id,
        children,
      }]
    })

    return [{
      title: '根目录',
      value: '__root__',
      children: toOptions(docTree),
    }]
  }, [docTree, movingNode])

  const moveNodeToParent = async (nodeId: string, parentId: string | null) => {
    const originalNode = findNodeInTree(docTree, nodeId)
    if (!originalNode) return
    if (parentId && isAncestorNode(originalNode, parentId)) {
      message.error('不能把父节点移动到自己的子节点下')
      return
    }

    const clone: DocumentTreeNode[] = JSON.parse(JSON.stringify(docTree))
    const moved = removeNodeFromTree(clone, nodeId)
    if (!moved) return

    if (!parentId) {
      clone.push(moved)
    } else {
      const parent = findNodeInTree(clone, parentId)
      if (!parent) {
        message.error('目标文件夹不存在')
        return
      }
      parent.children = parent.children || []
      parent.children.push(moved)
    }

    try {
      await documentApi.reorder(currentVersion, flattenForReorder(clone))
      message.success(parentId ? `已移动到「${findNodeInTree(docTree, parentId)?.title || '目标文件夹'}」` : '已移动到根目录')
      if (parentId) setExpandedKeys(keys => Array.from(new Set([...keys, parentId])))
      setMoveModalOpen(false)
      setMovingNode(null)
      await refreshTreeWithPulse()
    } catch (e: any) {
      message.error('移动失败: ' + (e?.response?.data?.detail || e?.message))
      loadDocTree()
    }
  }

  const handleTreeDrop = async (info: any) => {
    const dropKey = info.node.key as string
    const dragKey = info.dragNode.key as string
    if (dropKey === dragKey) return
    const dropPos = info.dropPosition as number  // -1=before, 0=inner, 1=after
    const dropToGap = info.dropToGap !== false

    // 克隆树, 找到 dragged 节点, 按 AntD 语义重定位
    const clone: DocumentTreeNode[] = JSON.parse(JSON.stringify(docTree))
    const removeAt = (nodes: DocumentTreeNode[], id: string): DocumentTreeNode | null => {
      for (let i = 0; i < nodes.length; i++) {
        if (nodes[i].id === id) return nodes.splice(i, 1)[0]
        if (nodes[i].children?.length) {
          const r = removeAt(nodes[i].children!, id)
          if (r) return r
        }
      }
      return null
    }
    // 简化: 直接走 AntD 语义, 重新扁平化
    // 1) 摘下 dragged
    const dragged = removeAt(clone, dragKey)
    if (!dragged) return

    // 2) 找到 dropKey 节点, 决定新 parent 和 index
    const findAndPlace = (nodes: DocumentTreeNode[]): boolean => {
      for (let i = 0; i < nodes.length; i++) {
        if (nodes[i].id === dropKey) {
          if (dropPos === 0 && !dropToGap) {
            // 作为子节点插入 (最前)
            nodes[i].children = nodes[i].children || []
            nodes[i].children.unshift(dragged)
          } else {
            // 作为兄弟节点插入 (before / after)
            const insertIdx = dropPos === -1 ? i : i + 1
            nodes.splice(insertIdx, 0, dragged)
          }
          return true
        }
        if (nodes[i].children?.length && findAndPlace(nodes[i].children)) return true
      }
      return false
    }
    // 排除循环: 如果 dragged 是 dropKey 的祖先, 不允许
    const isAncestor = (root: DocumentTreeNode, id: string): boolean => {
      if (root.id === id) return true
      return (root.children || []).some(c => isAncestor(c, id))
    }
    const findNode = (nodes: DocumentTreeNode[], id: string): DocumentTreeNode | null => {
      for (const n of nodes) {
        if (n.id === id) return n
        const r = findNode(n.children || [], id)
        if (r) return r
      }
      return null
    }
    const dropNode = findNode(clone, dropKey)
    if (dropNode && isAncestor(dragged, dropKey)) {
      message.error('不能把父节点拖到子节点下')
      return
    }
    findAndPlace(clone)

    // 3) 扁平化发到后端
    const flat = flattenForReorder(clone)
    try {
      await documentApi.reorder(currentVersion, flat)
      message.success('已重排')
      refreshTreeWithPulse()
    } catch (e: any) {
      message.error('重排失败: ' + (e?.response?.data?.detail || e?.message))
      loadDocTree()
    }
  }

  const handleDeleteDoc = async () => {
    if (!selectedDoc) return
    Modal.confirm({
      title: '确认删除',
      content: `删除文档「${selectedDoc.title}」？`,
      onOk: async () => {
        await documentApi.delete(selectedDoc.id)
        message.success('已删除')
        setSelectedDoc(null)
        setEditingContent('')
        loadDocTree()
      },
    })
  }

  const handleBuild = async () => {
    if (!currentVersion) return
    setBuilding(true)
    try {
      const res = await buildApi.trigger(currentVersion)
      if (res.data.data.status === 'success') {
        message.success('构建成功')
        // Admin需求 6-3: 4 段状态徽章 — 构建后立即更新 lastBuild
        setLastBuild({ version: versions.find(v => v.id === currentVersion)?.version || 'v?', at: res.data.data.created_at })
        setBuildSuccessPulse(true)
        if (buildPulseTimerRef.current) window.clearTimeout(buildPulseTimerRef.current)
        buildPulseTimerRef.current = window.setTimeout(() => setBuildSuccessPulse(false), 1800)
      } else {
        message.error('构建失败，请查看日志')
      }
    } catch {
      message.error('构建请求失败')
    } finally {
      setBuilding(false)
    }
  }

  // AI 面板动作处理（后续 P0-B-5 浮层会复用）
  const handleAIAction = (actionId: string) => {
    console.log('[AI action]', actionId)
    message.info(`AI 动作: ${actionId}（P0-B-5 浮层启用后真正触发）`)
  }

  // 递归把后端 tree 转换成 AntD Tree 需要的 treeData
  // 支持任意层级; 文件夹/子节点用 FolderOutlined
  // 长文件名截断用 titleRender + Tooltip
  // Admin R9 决策: 取消 R7 草稿过滤, 树全显所有 doc, draft 加灰标 (跟 published 站点 sidebar 一致)
  // 真因: 新建 doc 默认 status=draft, R7 草稿过滤把新 doc 滤掉, 用户感觉"树不更新"
  const toTreeData = useCallback((nodes: DocumentTreeNode[], depth: number = 0): any[] => {
    return nodes
      .map((doc) => {
        const hasChildren = doc.children && doc.children.length > 0
        const isFolder = doc.is_folder ?? hasChildren ?? false
        const isDraft = doc.status === 'draft'
        return {
          key: doc.id,
          title: (
            <div className="docs-tree-node" data-depth={depth} data-draft={isDraft ? 'true' : undefined}>
              <span className="docs-tree-node-icon">
                {isFolder ? <FolderOutlined /> : <FileTextOutlined />}
              </span>
              <Tooltip title={doc.title} placement="topLeft">
                <span className="docs-tree-node-title">{doc.title}</span>
              </Tooltip>
              <Dropdown
                trigger={['click']}
                menu={{
                  items: [
                    { key: 'add-doc', icon: <PlusOutlined />, label: '新建子文档', onClick: () => { setCreateParentId(doc.id); form.resetFields(); form.setFieldValue('isFolder', false); setModalOpen(true) } },
                    { key: 'add-folder', icon: <FolderAddOutlined />, label: '新建子文件夹', onClick: () => { setCreateParentId(doc.id); form.resetFields(); form.setFieldValue('isFolder', true); setModalOpen(true) } },
                    { key: 'move', icon: <FolderOpenOutlined />, label: '移动到...', onClick: () => openMoveModal(doc) },
                    { type: 'divider' },
                    { key: 'delete', icon: <DeleteOutlined />, label: '删除', danger: true, onClick: async () => {
                      Modal.confirm({
                        title: '确认删除',
                        content: `删除节点「${doc.title}」? 子节点会变 root`,
                        okButtonProps: { danger: true },
                        onOk: async () => { await documentApi.delete(doc.id); message.success('已删除'); loadDocTree() },
                      })
                    }},
                  ],
                }}
              >
                <Button type="text" size="small" icon={<MoreOutlined />} className="docs-tree-node-action" />
              </Dropdown>
            </div>
          ),
          children: hasChildren ? toTreeData(doc.children!, depth + 1) : undefined,
        }
      })
  }, [form])

  const treeData = useMemo(() => toTreeData(docTree), [docTree, toTreeData])

  // Tree header — 文档目录 + 上传/新建 icons (Admin反馈: 上传按钮放顶部, 跟着 Tree header, 别沉到底部)
  const treeHeader = (
    <div className="docs-tree-header">
      <Text className="docs-tree-title">文档目录</Text>
      <Space size={2}>
        <Tooltip title="批量上传 .md 文档">
          <Button
            type="text"
            size="small"
            icon={<InboxOutlined />}
            onClick={() => uploaderRef.current?.pick()}
            className="docs-tree-action"
            data-testid="docs-tree-upload-btn"
          />
        </Tooltip>
        <Tooltip title="移动当前选中节点">
          <Button
            type="text"
            size="small"
            icon={<FolderOpenOutlined />}
            onClick={() => openMoveModal(getSelectedTreeNode())}
            className="docs-tree-action"
            data-testid="docs-tree-move-btn"
          />
        </Tooltip>
        <Tooltip title="新建根文档">
          <Button
            type="text"
            size="small"
            icon={<PlusOutlined />}
            onClick={() => { setCreateParentId(null); form.resetFields(); setModalOpen(true) }}
            className="docs-tree-action"
            data-testid="docs-tree-add-btn"
          />
        </Tooltip>
      </Space>
    </div>
  )

  // 隐藏的 MarkdownUploader — 只用 ref 触发 pick(), 不显示自己的 trigger
  const hiddenUploader = currentVersion ? (
    <span className="docs-hidden-uploader" aria-hidden style={{ display: 'none' }}>
      <MarkdownUploader
        ref={uploaderRef}
        versionId={currentVersion}
        onUploaded={refreshTreeWithPulse}
        trigger={<span>hidden</span>}
      />
    </span>
  ) : null

  const middleSlot = (
    <>
      <Space.Compact style={{ width: '100%' }}>
        <Select
          value={currentVersion}
          onChange={(v) => { setCurrentVersion(v); setSelectedDoc(null) }}
          className="docs-version-select"
          size="small"
          style={{ flex: 1 }}
          options={versions.map(v => ({ value: v.id, label: v.version }))}
        />
        <Tooltip title="版本管理">
          <Button
            size="small"
            icon={<SettingOutlined />}
            onClick={() => setVersionDrawerOpen(true)}
            data-testid="version-manage-btn"
          />
        </Tooltip>
      </Space.Compact>
      <div className={`docs-tree-wrapper${treePulse ? ' docs-tree-wrapper--pulse' : ''}`}>
        {treeHeader}
        {loading ? (
          <Spin size="small" style={{ display: 'flex', justifyContent: 'center', padding: 24 }} />
        ) : (
          <Tree
            treeData={treeData}
            onSelect={(keys) => keys[0] && handleSelectDoc(keys[0] as string)}
            expandedKeys={expandedKeys}
            onExpand={(keys) => setExpandedKeys(keys as React.Key[])}
            onDrop={handleTreeDrop}
            draggable
            className="docs-tree"
            showLine
            blockNode
            virtual={false}
            showIcon={false}
          />
        )}
      </div>
    </>
  )

  return (
    <div className="docs-layout">
      {/* === 左栏 240px (AppSider + 中部 Tree) === */}
      <AppSider
        activeKey="/projects"
        subtitle={project?.name}
        topSlot={
          <div className="docs-sider-hint">
            <Text className="docs-sider-hint-text">{versions.length} 个版本</Text>
          </div>
        }
        middleSlot={middleSlot}
        showFooter={true}
      />
      {/* 隐藏的 MarkdownUploader — 上面 tree header inbox icon 通过 ref 触发 pick */}
      {hiddenUploader}

      {/* === 中栏 编辑器 === */}
      <main className="docs-main" ref={editorContainerRef}>
        <header className="docs-main-header">
          <div className="docs-main-header-left">
            <Button type="text" size="small" icon={<ArrowLeftOutlined />} onClick={() => navigate('/projects')}>返回项目列表</Button>
            {/* Admin R10: 面包屑 — 项目列表 / {项目} / 文档 */}
            <Breadcrumb
              className="docs-main-breadcrumb"
              items={[
                { title: <Link to="/projects">项目</Link> },
                { title: project ? <Link to={`/projects/${project.id}`}>{project.name}</Link> : '...' },
                { title: <Text type="secondary">文档</Text> },
              ]}
            />
            {selectedDoc ? (
              <Text strong className="docs-main-current-title">{selectedDoc.title}</Text>
            ) : selectedFolder ? (
              <Text strong className="docs-main-current-title">{selectedFolder.title}</Text>
            ) : (
              <Text type="secondary" className="docs-main-current-title docs-main-current-title--empty">未选择文档</Text>
            )}
            {project && (
              <Tag color="default" className="docs-main-version-tag">
                {project.name} · {versions.find(v => v.id === currentVersion)?.version}
              </Tag>
            )}
            {/* Admin需求 6-3: 4 段文档状态徽章 — 编辑中/已保存/已发布/已构建 */}
            {selectedDoc && (
              <StatusBadges
                dirty={editingContent !== savedContent}
                saving={saving}
                saveSuccess={saveSuccessPulse}
                savedAt={lastSavedAt}
                docStatus={selectedDoc.status as any}
                lastBuild={lastBuild}
                building={building}
                buildSuccess={buildSuccessPulse}
              />
            )}
          </div>
          <Space className="docs-main-header-actions">
            {/* R15: 构建是 version 级, 即使没选 doc 也能点 (拆出来) */}
            {currentVersion && (
              <Button size="small" type="primary" icon={<RocketOutlined />} onClick={() => setPreBuildOpen(true)}>构建</Button>
            )}
            {selectedDoc && (
              <>
                <Tooltip title="评论"><Button type="text" size="small" icon={<MessageOutlined />} /></Tooltip>
                <Tooltip title="历史"><Button type="text" size="small" icon={<HistoryOutlined />} /></Tooltip>
                <Button size="small" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>保存</Button>
                <Button size="small" icon={<EyeOutlined />} onClick={handlePublish}>发布</Button>
                <Button size="small" icon={<DeleteOutlined />} danger onClick={handleDeleteDoc} />
              </>
            )}
          </Space>
        </header>

        <div className={`docs-main-body${selectedDoc ? ' docs-main-body--editor' : ''}`} data-color-mode="light">
          {/* Admin R13: 没选 doc/folder 时, 显示 ProjectOverview 内容 (embedded) */}
          {!selectedDoc && !selectedFolder ? (
            project ? (
              <ProjectOverview
                embedded
                externalProject={project as any}
                externalVersions={versions}
                externalDocTree={docTree as any}
                externalBuilds={builds}
                onSelectDoc={(docId: string) => handleSelectDoc(docId)}
              />
            ) : (
              <div style={{ textAlign: 'center', paddingTop: '20vh' }}>
                <Spin />
              </div>
            )
          ) : selectedDoc ? (
            <MDEditor
              value={editingContent}
              onChange={(v) => setEditingContent(v || '')}
              height="100%"
              preview="live"
              visibleDragbar={false}
            />
          ) : selectedFolder ? (
            <FolderOverview
              folder={selectedFolder}
              allNodes={docTree}
              onOpenDoc={handleSelectDoc}
              onAddChildDoc={(folderId) => {
                setCreateParentId(folderId)
                form.resetFields()
                form.setFieldValue('isFolder', false)
                setModalOpen(true)
              }}
              onAddChildFolder={(folderId) => {
                setCreateParentId(folderId)
                form.resetFields()
                form.setFieldValue('isFolder', true)
                setModalOpen(true)
              }}
            />
          ) : (
            <div style={{ textAlign: 'center', paddingTop: '20vh' }}>
              <FileTextOutlined style={{ fontSize: 48, color: '#AEAEB2' }} />
              <div style={{ marginTop: 16 }}>
                <Text type="secondary">从左侧目录选择文档或文件夹</Text>
              </div>
              <Button type="primary" icon={<PlusOutlined />} style={{ marginTop: 16 }} onClick={() => setModalOpen(true)}>
                新建文档
              </Button>
            </div>
          )}
        </div>

        <StatusBar
          content={editingContent}
          dirty={editingContent !== savedContent}
          saving={saving}
          saveSuccess={saveSuccessPulse}
          lastSavedAt={lastSavedAt}
        />
      </main>

      {/* === 右栏 320px AI 面板 (可收折) === */}
      {!aiCollapsed && (
        <EditorAIPanel
          content={editingContent}
          projectName={project?.name}
          versionLabel={versions.find(v => v.id === currentVersion)?.version}
          docTitle={selectedDoc?.title}
          versionId={currentVersion || undefined}
          docId={selectedDoc?.id}
          onAction={handleAIAction}
        />
      )}

      {/* === AI 面板收折/展开按钮 — 贴在右栏边缘 === */}
      <Button
        type="text"
        size="small"
        icon={aiCollapsed ? <DoubleLeftOutlined /> : <DoubleRightOutlined />}
        onClick={() => setAiCollapsed(c => !c)}
        className="ai-panel-toggle"
        data-testid="ai-panel-toggle"
        title={aiCollapsed ? '展开 AI 面板' : '收起 AI 面板'}
      />

      {/* === 收折时的小条 (在 Sider 右下角) === */}
      {aiCollapsed && (
        <div className="ai-panel-collapsed" onClick={() => setAiCollapsed(false)} title="展开 AI 面板">
          <RobotOutlined style={{ fontSize: 16, color: 'var(--brand-primary)' }} />
          <Text className="ai-panel-collapsed-text">AI</Text>
        </div>
      )}

      {/* === AI 浮层（选中触发） === */}
      <AIFloatingActions
        editorRef={editorContainerRef}
        content={editingContent}
        onReplace={(newContent) => {
          setEditingContent(newContent)
        }}
        context={{
          project_name: project?.name,
          version: versions.find(v => v.id === currentVersion)?.version,
          doc_title: selectedDoc?.title,
        }}
      />

      {/* === R15: 预构建确认弹窗 === */}
      <PreBuildModal
        open={preBuildOpen}
        onClose={() => setPreBuildOpen(false)}
        versionId={currentVersion}
        versionName={versions.find(v => v.id === currentVersion)?.version}
        selectedDocId={selectedDoc?.id || null}
        selectedDocEditingContent={editingContent}
        selectedDocBaseRevision={docRevision}
        docTree={docTree}
        onTreeRefresh={loadDocTree}
        onAfterBuild={(b) => {
          // 跟 handleBuild 一样的副作用: 更新 lastBuild + pulse
          setLastBuild({
            version: versions.find(v => v.id === currentVersion)?.version || 'v?',
            at: b.created_at,
          })
          setBuildSuccessPulse(true)
          if (buildPulseTimerRef.current) window.clearTimeout(buildPulseTimerRef.current)
          buildPulseTimerRef.current = window.setTimeout(() => setBuildSuccessPulse(false), 1800)
        }}
      />

      <Modal
        title={`发现编辑冲突：${conflict?.docTitle || ''}`}
        open={!!conflict}
        width={1120}
        onCancel={() => setConflict(null)}
        footer={[
          <Button key="server" onClick={handleUseServerVersion}>
            载入服务器版本
          </Button>,
          <Button key="copy" onClick={handleSaveConflictCopy} loading={saving}>
            我的修改另存为副本
          </Button>,
          <Button key="save" type="primary" onClick={handleSaveMergedConflict} loading={saving}>
            保存合并结果
          </Button>,
        ]}
      >
        {conflict && (
          <div>
            <Alert
              type="warning"
              showIcon
              message="这篇文档在你编辑期间已被其他人保存"
              description={`你打开时的版本是 r${conflict.baseRevision ?? '-'}, 服务器当前版本是 r${conflict.latestRevision}。请对比差异, 调整下方合并结果后再保存。`}
              style={{ marginBottom: 16 }}
            />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
              <div>
                <Text strong>服务器最新版本</Text>
                <div style={{ marginTop: 8, border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden', maxHeight: 260, overflowY: 'auto', background: '#fff' }}>
                  {conflictRows.map(row => (
                    <pre
                      key={`server-${row.line}`}
                      style={{
                        margin: 0,
                        padding: '4px 10px',
                        minHeight: 24,
                        whiteSpace: 'pre-wrap',
                        fontSize: 12,
                        background: row.changed ? (row.onlyDraft ? '#fff7ed' : '#fff1f0') : '#fff',
                        borderBottom: '1px solid #f0f0f0',
                      }}
                    >
                      <span style={{ color: '#999', marginRight: 8 }}>{row.line}</span>
                      {row.onlyDraft ? '' : row.server}
                    </pre>
                  ))}
                </div>
              </div>
              <div>
                <Text strong>我的编辑副本</Text>
                <div style={{ marginTop: 8, border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden', maxHeight: 260, overflowY: 'auto', background: '#fff' }}>
                  {conflictRows.map(row => (
                    <pre
                      key={`draft-${row.line}`}
                      style={{
                        margin: 0,
                        padding: '4px 10px',
                        minHeight: 24,
                        whiteSpace: 'pre-wrap',
                        fontSize: 12,
                        background: row.changed ? (row.onlyServer ? '#f6ffed' : '#fffbe6') : '#fff',
                        borderBottom: '1px solid #f0f0f0',
                      }}
                    >
                      <span style={{ color: '#999', marginRight: 8 }}>{row.line}</span>
                      {row.onlyServer ? '' : row.draft}
                    </pre>
                  ))}
                </div>
              </div>
            </div>
            <Text strong>合并后的 Markdown</Text>
            <TextArea
              value={mergeContent}
              onChange={(e) => setMergeContent(e.target.value)}
              rows={10}
              style={{ marginTop: 8, fontFamily: 'var(--font-mono, monospace)' }}
            />
          </div>
        )}
      </Modal>

      <Modal
        title={createParentId ? '新建子节点' : '新建文档'}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setCreateParentId(null); form.resetFields() }}
        onOk={() => form.submit()}
        okText="创建"
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleCreateDoc} initialValues={{ isFolder: false }}>
          <Form.Item name="isFolder" label="类型" style={{ marginBottom: 12 }}>
            <Segmented
              block
              options={[
                { label: '文档', value: false, icon: <FileTextOutlined /> },
                { label: '文件夹', value: true, icon: <FolderOutlined /> },
              ]}
            />
          </Form.Item>
          <Form.Item shouldUpdate={(prev, curr) => prev.isFolder !== curr.isFolder} noStyle>
            {() => {
              const isFolder = form.getFieldValue('isFolder')
              return (
                <>
                  <Form.Item name="title" label={isFolder ? '文件夹名' : '标题'} rules={[{ required: true }]}>
                    <Input placeholder={isFolder ? '例: API 设计规范 / 高级工程篇' : '例: 快速入门 / 架构设计'} autoFocus />
                  </Form.Item>
                  {!isFolder && (
                    <Form.Item name="slug" label="URL 标识" extra="可自定义, 用于生成 published 站点的访问路径 (slug.html)">
                      <Input placeholder="自动生成 (可修改)" />
                    </Form.Item>
                  )}
                </>
              )
            }}
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="移动到文件夹"
        open={moveModalOpen}
        okText="移动"
        cancelText="取消"
        onCancel={() => { setMoveModalOpen(false); setMovingNode(null); setMoveTargetId(null) }}
        onOk={() => movingNode && moveNodeToParent(movingNode.id, moveTargetId)}
        okButtonProps={{ disabled: !movingNode }}
        destroyOnClose
      >
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Text type="secondary" style={{ fontSize: 13 }}>
            将「{movingNode?.title || '-'}」移动到：
          </Text>
          <TreeSelect
            treeData={folderTreeOptions}
            value={moveTargetId || '__root__'}
            onChange={(value) => setMoveTargetId(value === '__root__' ? null : value)}
            treeDefaultExpandAll
            style={{ width: '100%' }}
            placeholder="选择目标文件夹"
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            拖拽仍可用于快速排序；这个入口适合精确地把文档放入新建文件夹。
          </Text>
        </Space>
      </Modal>

      {/* R6 反馈 2: 版本管理抽屉 */}
      <VersionManageDrawer
        open={versionDrawerOpen}
        onClose={() => setVersionDrawerOpen(false)}
        projectId={projectId!}
        versions={versions}
        onChange={() => {
          // 刷新版本列表
          if (projectId) versionApi.list(projectId).then(res => {
            const vers = res.data.data || []
            setVersions(vers)
            if (!vers.find((v: any) => v.id === currentVersion)) {
              const def = vers.find((v: any) => v.is_default) || vers[0]
              if (def) setCurrentVersion(def.id)
            }
          })
        }}
      />
    </div>
  )
}
