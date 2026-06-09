/**
 * ProjectContextPanel — 进 /projects/:id 时, 左侧 sider 顶部显示项目上下文
 *
 * Admin R12 反馈: "/projects/:id 的侧边菜单栏, 应该和 /docs 的菜单栏显示的内容一致"
 *
 * /docs 页 sider 顶部: subtitle={project?.name} + topSlot=<div>{versions.length} 个版本</div>
 * 复刻同样的内容: 项目名 + "N 个版本" 提示
 *
 * 之前我加了 logo + 5 数字 + 4 link 太多, 跟 docs 不一致, Admin要 "一致" 而非 "丰富"
 * 修法: 删 logo/5 数字/4 link, 只保留 ← 返回项目列表 + 项目名 + N 个版本
 */
import { Link } from 'react-router-dom'
import { Typography } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import '../styles/project-context-panel.css'

const { Text } = Typography

export interface ProjectContextPanelProps {
  /** 项目名 (跟 /docs 页 AppSider subtitle 一致) */
  name?: string
  /** 版本数 (跟 /docs 页 topSlot 提示一致) */
  versionCount: number
}

export default function ProjectContextPanel({ name, versionCount }: ProjectContextPanelProps) {
  return (
    <div className="project-context-panel" data-testid="project-context-panel">
      {/* 返回项目列表 — 顶部一行小链接 */}
      <Link to="/projects" className="project-context-back" data-testid="project-context-back">
        <ArrowLeftOutlined /> 返回项目列表
      </Link>

      {/* 项目名 — 跟 /docs 页 AppSider subtitle 一致, 但走 topSlot 路径避免重复显示 */}
      {name && (
        <Text className="project-context-name-hint" ellipsis={{ tooltip: name }}>{name}</Text>
      )}

      {/* 版本数提示 — 跟 /docs 页 topSlot 一致 */}
      <div className="docs-sider-hint">
        <Text className="docs-sider-hint-text">{versionCount} 个版本</Text>
      </div>
    </div>
  )
}
