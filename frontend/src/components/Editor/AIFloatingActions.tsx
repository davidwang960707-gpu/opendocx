/** AIFloatingActions — 选中内容触发的底部 AI 浮层
 *
 * P0-B-5: 编辑器选中文本时浮出，6 个 AI 动作。
 * - 检测文本选择变化，自动浮出
 * - 点动作 → 调后端 SSE 流 → 弹出"接受/拒绝"对比 Modal
 * - 接受 → 替换原 content；拒绝 → 丢弃
 *
 * 6 个动作（按设计稿）：
 *   continue  续写   rewrite  重写
 *   explain   解释   qa       问答
 *   summarize 总结   polish   润色
 * + 更多下拉（生成测试 / 生成接口 / 优化文案）
 */
import { useEffect, useState, useRef, useCallback } from 'react'
import { Modal, Button, Spin, message } from 'antd'
import {
  EditOutlined, SyncOutlined, QuestionCircleOutlined,
  FileSearchOutlined, CompressOutlined, StarOutlined,
  CheckOutlined, CloseOutlined, ThunderboltOutlined, DownOutlined,
  CodeOutlined, FileTextOutlined, SendOutlined,
} from '@ant-design/icons'
import { editorApi, type AIAction } from '../../services/editorApi'

interface Props {
  /** 编辑器容器 ref（监听 selection 变化） */
  editorRef: React.RefObject<HTMLElement | null>
  /** 当前文档全文（content / selection 上下文） */
  content: string
  /** 流结束后用户接受新文本，回调替换 */
  onReplace: (newContent: string) => void
  /** 上下文（项目/版本/文档） */
  context?: Record<string, any>
}

/** R13 fix: 记录 selection 的原始 (untrimmed) 文本 + 起止位置
 * 之前只用 trim 后的 text 找位置, 但 trim 之后 text.length 和 start..end 区间长度对不上
 * → content.indexOf(selText) 经常 -1 → 接受替换走"末尾追加"兜底分支
 */
interface SelectionRange {
  text: string       // trim 后的, 用于显示/LLM 上下文
  start: number      // textarea 字符位置 (不 trim)
  end: number        // textarea 字符位置 (不 trim)
}

interface PendingChange {
  action: string
  label: string
  original: string
  generated: string
  fullContent: string
  selectionStart: number
  selectionEnd: number
}

const PRIMARY_ACTIONS = [
  { id: 'continue',  label: '续写',  icon: <EditOutlined />,        needs: ['content'] },
  { id: 'rewrite',   label: '重写',  icon: <SyncOutlined />,        needs: ['selection'] },
  { id: 'explain',   label: '解释',  icon: <QuestionCircleOutlined />, needs: ['selection'] },
  { id: 'qa',        label: '问答',  icon: <FileSearchOutlined />,  needs: ['content'] },
  { id: 'summarize', label: '总结',  icon: <CompressOutlined />,    needs: ['content'] },
  { id: 'polish',    label: '润色',  icon: <StarOutlined />,        needs: ['selection'] },
] as const

const MORE_ACTIONS = [
  { id: 'generate-tests',  label: '生成测试',  icon: <CodeOutlined /> },
  { id: 'generate-openapi', label: '生成接口',  icon: <FileTextOutlined /> },
  { id: 'improve',          label: '优化文案',  icon: <StarOutlined /> },
]

export default function AIFloatingActions({ editorRef, content, onReplace, context }: Props) {
  const [visible, setVisible] = useState(false)
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null)
  const [selectedText, setSelectedText] = useState('')
  // R13 fix: 同时存 selection 区间, 用于精确替换 (不用 indexOf 二次匹配)
  const [selectionRange, setSelectionRange] = useState<SelectionRange | null>(null)
  const [moreOpen, setMoreOpen] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [pending, setPending] = useState<PendingChange | null>(null)
  const [streamingText, setStreamingText] = useState('')
  const [qaQuestion, setQaQuestion] = useState('')
  const [showQaInput, setShowQaInput] = useState(false)
  const [tipQuery, setTipQuery] = useState('')
  const tipInputRef = useRef<HTMLInputElement | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // 监听 selection 变化
  useEffect(() => {
    const root = editorRef.current
    if (!root) return
    // 用 mouseup/keyup/mouseup 替代 selectionchange（后者在 textarea 上不更新 isCollapsed）
    const compute = (e?: MouseEvent) => {
      const active = document.activeElement
      if (!active || !root.contains(active)) {
        setVisible(false)
        return
      }
      // 优先尝试 textarea/input 的 selection
      if (active instanceof HTMLTextAreaElement || active instanceof HTMLInputElement) {
        const start = active.selectionStart
        const end = active.selectionEnd
        if (start === null || end === null || start === end) {
          setVisible(false)
          return
        }
        // R13 fix: 用未 trim 的 raw 区间记录 start/end, 但显示用 trim 后的 text
        const rawText = active.value.substring(start, end)
        const text = rawText.trim()
        if (text.length < 2) {
          setVisible(false)
          return
        }
        setSelectedText(text)
        // R13 fix: 存完整区间 (start/end 是 raw 位置, 跟 content.slice(start, end) 对得上)
        setSelectionRange({ text, start, end })
        const rootRect = root.getBoundingClientRect()
        // 追随鼠标：贴近 mouseup 位置
        if (e) {
          const x = e.clientX - rootRect.left
          const y = e.clientY - rootRect.top
          // 浮层约 360×44；底部边界检测
          const flipY = (y + 60 > rootRect.height) // 选区靠下 → 浮层放到鼠标上方
          setPosition({
            top: flipY ? y - 52 : y + 16,
            left: Math.max(8, Math.min(x + 12, rootRect.width - 380)),
          })
        } else {
          // 键盘选区 → 退化到选区文本下方
          const rect = active.getBoundingClientRect()
          setPosition({
            top: rect.bottom - rootRect.top + 8,
            left: rect.left - rootRect.left + rect.width / 2,
          })
        }
        setVisible(true)
        return
      }
      // contentEditable fallback
      const sel = window.getSelection()
      if (!sel || sel.isCollapsed) {
        setVisible(false)
        return
      }
      const text = sel.toString().trim()
      if (text.length < 2) {
        setVisible(false)
        return
      }
      setSelectedText(text)
      const rootRect = root.getBoundingClientRect()
      if (e) {
        const x = e.clientX - rootRect.left
        const y = e.clientY - rootRect.top
        const flipY = (y + 60 > rootRect.height)
        setPosition({
          top: flipY ? y - 52 : y + 16,
          left: Math.max(8, Math.min(x + 12, rootRect.width - 380)),
        })
      } else {
        const range = sel.getRangeAt(0)
        const rect = range.getBoundingClientRect()
        setPosition({
          top: rect.bottom - rootRect.top + 8,
          left: rect.left - rootRect.left + rect.width / 2,
        })
      }
      setVisible(true)
    }
    // 鼠标松开后算一次（带事件用于定位）
    const onMouseUp = (e: MouseEvent) => setTimeout(() => compute(e), 10)
    // 键盘 shift+arrow 选区变化
    const onKeyUp = (e: KeyboardEvent) => {
      if (e.shiftKey || ['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(e.key)) {
        setTimeout(() => compute(), 10)
      }
    }
    root.addEventListener('mouseup', onMouseUp)
    root.addEventListener('keyup', onKeyUp)
    return () => {
      root.removeEventListener('mouseup', onMouseUp)
      root.removeEventListener('keyup', onKeyUp)
    }
  }, [editorRef])

  // 关闭"更多"下拉当点击外部
  useEffect(() => {
    if (!moreOpen) return
    const close = () => setMoreOpen(false)
    setTimeout(() => document.addEventListener('click', close, { once: true }), 0)
    return () => document.removeEventListener('click', close)
  }, [moreOpen])

  // 浮层显示时自动聚焦内联 query 输入框 (R11)
  useEffect(() => {
    if (visible) {
      // 浮层刚显示 → 等动画完成后聚焦, 避免抢 selection
      const t = setTimeout(() => {
        tipInputRef.current?.focus()
        // 如果有选中文字, 把 query 默认填上 "解释/重写..." placeholder 不变, 用户自己改
      }, 50)
      return () => clearTimeout(t)
    } else {
      // 浮层隐藏时清空 query, 下次重新进入不残留
      setTipQuery('')
    }
  }, [visible])

  // 触发动作（统一入口）
  const trigger = useCallback(async (
    actionId: string,
    label: string,
    prefill?: { question?: string; selection?: string; selectionStart?: number; selectionEnd?: number },
  ) => {
    setVisible(false)
    setMoreOpen(false)

    // qa 需要先问问题 (R11: tip 内联输入已可直接传 prefill.question, 跳过 Modal)
    if (actionId === 'qa' && !prefill?.question) {
      setShowQaInput(true)
      Modal.confirm({
        title: '向 AI 提问',
        content: (
          <input
            autoFocus
            value={qaQuestion}
            onChange={(e) => setQaQuestion(e.target.value)}
            placeholder="基于当前文档内容提问"
            style={{ width: '100%', padding: 8, border: '1px solid #D2D2D7', borderRadius: 6, marginTop: 8 }}
          />
        ),
        okText: '提问',
        cancelText: '取消',
        onOk: () => {
          if (!qaQuestion.trim()) {
            message.warning('请输入问题')
            return Promise.reject()
          }
          runAction(actionId, label, { question: qaQuestion })
          setQaQuestion('')
          setShowQaInput(false)
        },
        onCancel: () => {
          setQaQuestion('')
          setShowQaInput(false)
        },
      })
      return
    }

    // "更多"里的动作：本地映射到后端 action（生成测试/接口/优化文案 → 续写语义）
    const realAction =
      actionId === 'generate-tests'  ? 'continue' :
      actionId === 'generate-openapi' ? 'continue' :
      actionId === 'improve'          ? 'polish' :
      actionId

    // 计算 selection 位置 (R13 fix: 用 state 里存的区间, 不用 indexOf 二次匹配)
    // 因为 trim 后的 text 跟 start..end 区间长度对不上, indexOf 经常 -1
    const selText = prefill?.selection ?? selectedText
    let selectionStart = -1
    let selectionEnd = -1
    if (selectionRange && selectionRange.text === selText) {
      // state 里的区间跟当前 selText 匹配 → 直接用
      selectionStart = selectionRange.start
      selectionEnd = selectionRange.end
    } else if (selText) {
      // 兜底: indexOf (content 是 prop, 同步的)
      const idx = content.indexOf(selText)
      if (idx >= 0) {
        selectionStart = idx
        selectionEnd = idx + selText.length
      }
    }

    runAction(realAction, label, {
      selection: selText,
      question: prefill?.question,
      selectionStart,
      selectionEnd,
    })
  }, [content, selectedText, qaQuestion, selectionRange])

  const runAction = async (
    actionId: string,
    label: string,
    extra: { selection?: string; question?: string; selectionStart?: number; selectionEnd?: number },
  ) => {
    setStreaming(true)
    setStreamingText('')
    abortRef.current = new AbortController()
    let full = ''
    try {
      for await (const ev of editorApi.streamAction({
        action: actionId,
        content,
        selection: extra.selection,
        question: extra.question,
        context,
        temperature: 0.7,
        max_tokens: 2048,
      })) {
        if (ev.event === 'token') full += ev.data.delta
        else if (ev.event === 'meta') {
          // 可以在这里显示 model name
        } else if (ev.event === 'error') {
          message.error(`AI 出错: ${ev.data.message}`)
          break
        }
        setStreamingText(full)
      }
    } catch (e: any) {
      message.error(`请求失败: ${e.message}`)
    } finally {
      setStreaming(false)
    }
    if (full) {
      setPending({
        action: actionId,
        label,
        original: extra.selection || '',
        generated: full,
        fullContent: content,
        selectionStart: extra.selectionStart ?? -1,
        selectionEnd: extra.selectionEnd ?? -1,
      })
    }
  }

  const accept = () => {
    if (!pending) return
    let newContent: string
    if (pending.selectionStart >= 0 && pending.selectionEnd > pending.selectionStart) {
      // 替换选区
      newContent =
        pending.fullContent.slice(0, pending.selectionStart) +
        pending.generated +
        pending.fullContent.slice(pending.selectionEnd)
    } else {
      // 续写 / 总结 / qa：追加到末尾（前后留空行）
      const sep = pending.fullContent.endsWith('\n') ? '\n' : '\n\n'
      newContent = pending.fullContent + sep + pending.generated
    }
    onReplace(newContent)
    message.success(`已应用：${pending.label}`)
    setPending(null)
    setStreamingText('')
  }

  const reject = () => {
    setPending(null)
    setStreamingText('')
  }

  if (!position) return null

  return (
    <>
      {/* 浮层：贴近鼠标 (P1 改进) */}
      {visible && (
        <div
          className="ai-floating-popup ai-floating-popup--cursor"
          style={{
            top: position.top,
            left: position.left,
          }}
          onMouseDown={(e) => e.preventDefault()} /* 防止点浮层时 selection 消失 */
        >
          {/* 内联 Query 输入框 (R11 升级): 选中内容后用户直接输入问题 → 回车/点发送触发 AI */}
          <form
            className="ai-floating-tip"
            onSubmit={(e) => {
              e.preventDefault()
              const v = tipQuery.trim()
              if (!v) return
              // R13 fix: 透传 selectedText 让 qa 走"基于选区"语义
              // trigger() 内部会从 selectionRange state 取精确 start/end
              trigger('qa', '问答', { question: v, selection: selectedText })
            }}
          >
            <span className="ai-floating-tip-dot" aria-hidden />
            <input
              ref={tipInputRef}
              className="ai-floating-tip-input"
              type="text"
              value={tipQuery}
              onChange={(e) => setTipQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') {
                  e.preventDefault()
                  setVisible(false)
                }
              }}
              onClick={(e) => e.stopPropagation()}
              onMouseDown={(e) => e.stopPropagation()}
              placeholder="选中内容，AI 帮你快速处理 (回车发送)"
              disabled={streaming}
              aria-label="向 AI 提问"
            />
            <button
              type="submit"
              className="ai-floating-tip-send"
              disabled={streaming || !tipQuery.trim()}
              title="发送 (Enter)"
              aria-label="发送"
            >
              <SendOutlined />
            </button>
          </form>
          <div className="ai-floating-actions">
            {PRIMARY_ACTIONS.map(a => (
              <button
                key={a.id}
                className="ai-floating-btn"
                disabled={streaming}
                onClick={() => trigger(a.id, a.label)}
              >
                {a.icon}
                <span>{a.label}</span>
              </button>
            ))}
            <div className="ai-floating-more">
              <button
                className="ai-floating-btn"
                disabled={streaming}
                onClick={(e) => { e.stopPropagation(); setMoreOpen(v => !v) }}
              >
                更多
                <DownOutlined style={{ fontSize: 9 }} />
              </button>
              {moreOpen && (
                <div className="ai-floating-more-menu">
                  {MORE_ACTIONS.map(a => (
                    <div
                      key={a.id}
                      className="ai-floating-more-item"
                      onClick={() => trigger(a.id, a.label)}
                    >
                      {a.icon}
                      <span>{a.label}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 流式预览 Modal — 接受/拒绝 */}
      <Modal
        open={!!pending || streaming}
        onCancel={reject}
        footer={null}
        width={720}
        title={
          <span>
            <ThunderboltOutlined style={{ color: '#4F46E5', marginRight: 8 }} />
            {pending?.label || 'AI 生成中...'}
          </span>
        }
        maskClosable={false}
        destroyOnHidden
      >
        {streaming && !pending && (
          <div style={{ padding: '40px 0', textAlign: 'center' }}>
            <Spin />
            <div style={{ marginTop: 12, color: '#6E6E73', fontSize: 13 }}>
              AI 正在生成...
            </div>
            {streamingText && (
              <pre className="ai-stream-preview">{streamingText}</pre>
            )}
          </div>
        )}
        {pending && (
          <>
            {pending.original && (
              <div className="ai-diff-section">
                <div className="ai-diff-label">原文</div>
                <pre className="ai-diff-original">{pending.original}</pre>
              </div>
            )}
            <div className="ai-diff-section">
              <div className="ai-diff-label" style={{ color: '#4F46E5' }}>
                AI 生成（{pending.generated.length} 字）
              </div>
              <pre className="ai-diff-generated">{pending.generated}</pre>
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
              <Button icon={<CloseOutlined />} onClick={reject}>
                拒绝
              </Button>
              <Button type="primary" icon={<CheckOutlined />} onClick={accept}>
                接受并替换
              </Button>
            </div>
          </>
        )}
      </Modal>
    </>
  )
}
