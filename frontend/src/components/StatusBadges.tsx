/**
 * StatusBadges — 4 段文档状态徽章
 *
 * 状态定义（参考 FolderOverview + 编辑器 StatusBar 风格统一）:
 *  1. 编辑中  (有未保存修改)    橙 ●   "编辑中"
 *  2. 已保存  (内容已持久化)    绿 ✓   "已保存 · {n} 分钟前" (默认)
 *  3. 已发布  (status=published) 紫 ✓✓  "已发布" (默认版本)
 *  4. 已构建  (有最近 build)   蓝 ↑   "{version} 构建于 {t}"
 *
 * 设计原则: 4 段用 Space compact 排开, 不可达的状态变灰 (不隐藏, 让用户看到 4 段在)
 *           不可达有 hover 提示: "尚未保存" / "尚未发布" / "尚未构建"
 *
 * Props:
 *   - dirty: editingContent !== savedContent
 *   - savedAt: timestamp (number) of last save
 *   - docStatus: 'draft' | 'published' | 'archived'
 *   - lastBuild: { version, at } | null
 *
 * Admin需求 6-3 P2: "编辑页面应该有文档的状态: 编辑中/已保存/已发布/已构建?"
 */
import { Space, Tooltip } from 'antd'
import { EditOutlined, CheckCircleOutlined, RocketOutlined, CheckOutlined } from '@ant-design/icons'
import { formatDistanceToNow } from '../utils/time'

interface StatusBadgesProps {
  dirty: boolean
  saving?: boolean
  saveSuccess?: boolean
  savedAt: number | null
  docStatus?: 'draft' | 'published' | 'archived'
  lastBuild?: { version: string; at: string } | null
  building?: boolean
  buildSuccess?: boolean
  size?: 'small' | 'default'
}

function formatTime(ts: number | null): string {
  if (!ts) return '—'
  return formatDistanceToNow(new Date(ts))
}

export default function StatusBadges({
  dirty,
  saving = false,
  saveSuccess = false,
  savedAt,
  docStatus = 'draft',
  lastBuild = null,
  building = false,
  buildSuccess = false,
  size = 'small',
}: StatusBadgesProps) {
  // 编辑中: 有未保存修改 (priority 最高, 其它 3 段变灰)
  const isEditing = dirty && !saving

  // 已保存: 最近保存过 (默认显示)
  const savedReached = !!savedAt

  // 已发布: docStatus === 'published'
  const isPublished = docStatus === 'published'

  // 已构建: lastBuild 存在
  const isBuilt = !!lastBuild

  // 4 段样式 - 当前激活色 / 未到达色
  const editingColor = saving || isEditing ? '#FF9500' : 'var(--text-tertiary)'
  const savedColor = saving || isEditing ? 'var(--text-tertiary)' : '#34C759'
  const publishedColor = isPublished ? '#8B7FE8' : 'var(--text-tertiary)'
  const builtColor = building ? '#FF9500' : buildSuccess || isBuilt ? '#4F46E5' : 'var(--text-tertiary)'

  // 编辑中提示
  const editingTip = saving ? '正在保存当前修改' : isEditing ? '当前有未保存的修改' : '内容已保存, 无未保存修改'

  // 已保存提示
  const savedTip = savedReached ? `最后保存于 ${formatTime(savedAt)}` : '尚未保存'

  // 已发布提示
  const publishedTip = isPublished
    ? '此文档已发布, 在 published 站点可访问'
    : docStatus === 'archived'
    ? '此文档已归档, 不参与构建'
    : '草稿状态, 尚未发布'

  // 已构建提示
  const builtTip = building
    ? '正在构建当前版本'
    : buildSuccess
    ? '构建成功, 已更新 published 站点'
    : isBuilt && lastBuild
    ? `版本 ${lastBuild.version} 构建于 ${formatTime(new Date(lastBuild.at).getTime())}`
    : '尚未触发构建, published 站点不包含此文档'

  const fontSize = size === 'small' ? 11 : 12

  return (
    <Space size={6} wrap data-testid="status-badges">
      <Tooltip title={editingTip}>
        <span className={`status-badge${saving ? ' status-badge--busy' : ''}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: editingColor, fontSize, fontWeight: 500 }}>
          <span style={{
            display: 'inline-block', width: 6, height: 6, borderRadius: '50%',
            background: editingColor, boxShadow: isEditing || saving ? `0 0 0 2px ${editingColor}30` : 'none',
          }} />
          {saving ? '保存中' : isEditing ? '编辑中' : '已保存'}
        </span>
      </Tooltip>

      <span style={{ color: 'var(--text-tertiary)', fontSize }}>·</span>

      <Tooltip title={savedTip}>
        <span className={`status-badge${saveSuccess ? ' status-badge--success' : ''}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: savedColor, fontSize }}>
          <CheckCircleOutlined style={{ fontSize: fontSize + 2 }} />
          {saving ? '保存中' : saveSuccess ? '刚刚保存' : savedReached ? `已保存 ${formatTime(savedAt)}` : '未保存'}
        </span>
      </Tooltip>

      <span style={{ color: 'var(--text-tertiary)', fontSize }}>·</span>

      <Tooltip title={publishedTip}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: publishedColor, fontSize, fontWeight: isPublished ? 500 : 400 }}>
          {isPublished ? <CheckOutlined style={{ fontSize: fontSize + 2 }} /> : <EditOutlined style={{ fontSize: fontSize + 1 }} />}
          {isPublished ? '已发布' : docStatus === 'archived' ? '已归档' : '未发布'}
        </span>
      </Tooltip>

      <span style={{ color: 'var(--text-tertiary)', fontSize }}>·</span>

      <Tooltip title={builtTip}>
        <span className={`status-badge${building ? ' status-badge--busy' : buildSuccess ? ' status-badge--success' : ''}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: builtColor, fontSize, fontWeight: isBuilt || building || buildSuccess ? 500 : 400 }}>
          <RocketOutlined style={{ fontSize: fontSize + 1 }} />
          {building ? '构建中' : buildSuccess ? '构建成功' : isBuilt && lastBuild ? `${lastBuild.version} 构建于 ${formatTime(new Date(lastBuild.at).getTime())}` : '未构建'}
        </span>
      </Tooltip>
    </Space>
  )
}
