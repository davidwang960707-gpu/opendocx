/** MarkdownUploader — P1-UI-3 本地 Markdown 上传
 *
 * 触发位置：文档树头部 + 号按钮（hover 显示"上传 .md"）
 * 行为：
 *   - 点击触发文件选择（accept=.md,.markdown,multiple）
 *   - 拖拽到上传区也支持
 *   - 选完文件调 /api/v1/versions/{vid}/documents/import
 *   - 进度 / 成功 / 失败 toast
 *   - 完成后回调 onUploaded 刷新文档树
 */
import { useState, useRef, useCallback, forwardRef, useImperativeHandle } from 'react'
import { Button, Modal, message, Tag, Tooltip, Space } from 'antd'
import { InboxOutlined, FileTextOutlined, CheckCircleFilled, CloseCircleFilled } from '@ant-design/icons'
import { documentApi } from '../../services/api'

export interface MarkdownUploaderRef {
  /** 手动触发文件选择 (用于 Tree header inbox icon 调) */
  pick: () => void
}

interface Props {
  versionId: string
  onUploaded?: () => void
  /** 自定义触发器（不传则用默认图标按钮） */
  trigger?: React.ReactElement
}

interface UploadResult {
  imported: Array<{ id: string; title: string; slug: string }>
  errors: Array<{ filename: string; message: string }>
}

export default forwardRef<MarkdownUploaderRef, Props>(function MarkdownUploader({ versionId, onUploaded, trigger }: Props, ref) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [pending, setPending] = useState<File[]>([])
  const [result, setResult] = useState<UploadResult | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useImperativeHandle(ref, () => ({
    pick: () => fileInputRef.current?.click(),
  }), [])

  const reset = () => {
    setPending([])
    setResult(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleFiles = useCallback((files: FileList | null) => {
    if (!files || files.length === 0) return
    const list = Array.from(files).filter(f => /\.(md|markdown)$/i.test(f.name))
    if (list.length === 0) {
      message.warning('请选择 .md 或 .markdown 文件')
      return
    }
    setPending(list)
    setOpen(true)
  }, [])

  const doUpload = async () => {
    if (pending.length === 0) return
    setBusy(true)
    try {
      const res = await documentApi.importMarkdown(versionId, pending)
      const data: UploadResult = res.data?.data || { imported: [], errors: [] }
      setResult(data)
      if (data.imported.length > 0) {
        message.success(`成功导入 ${data.imported.length} 个文档`)
        onUploaded?.()
      }
      if (data.errors.length > 0) {
        message.warning(`${data.errors.length} 个文件失败`)
      }
    } catch (e: any) {
      message.error(`上传失败: ${e.response?.data?.detail || e.message}`)
    } finally {
      setBusy(false)
    }
  }

  const close = () => {
    if (busy) return
    setOpen(false)
    setTimeout(reset, 300)
  }

  return (
    <>
      {trigger ? (
        <span
          onClick={() => fileInputRef.current?.click()}
          style={{ display: 'inline-flex', width: '100%' }}
        >
          {trigger}
        </span>
      ) : (
        <Tooltip title="上传本地 .md 文档（支持批量）">
          <Button
            type="text"
            size="small"
            icon={<InboxOutlined />}
            onClick={() => fileInputRef.current?.click()}
            data-testid="md-upload-btn"
          />
        </Tooltip>
      )}
      <input
        ref={fileInputRef}
        type="file"
        accept=".md,.markdown"
        multiple
        style={{ display: 'none' }}
        onChange={(e) => handleFiles(e.target.files)}
      />

      <Modal
        open={open}
        onCancel={close}
        footer={null}
        title="上传 Markdown 文档"
        width={520}
      >
        {result ? (
          // 结果视图
          <div>
            {result.imported.length > 0 && (
              <section style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <CheckCircleFilled style={{ color: '#34C759' }} /> 成功导入 {result.imported.length} 个
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {result.imported.map(d => (
                    <div key={d.id} style={{
                      padding: '6px 10px', background: 'var(--bg-secondary)',
                      borderRadius: 6, fontSize: 13,
                      display: 'flex', alignItems: 'center', gap: 8,
                    }}>
                      <FileTextOutlined style={{ color: 'var(--brand-primary)' }} />
                      <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{d.title}</span>
                      <Tag style={{ margin: 0, fontSize: 10, color: 'var(--text-tertiary)' }}>/{d.slug}</Tag>
                    </div>
                  ))}
                </div>
              </section>
            )}
            {result.errors.length > 0 && (
              <section>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <CloseCircleFilled style={{ color: '#FF3B30' }} /> 失败 {result.errors.length} 个
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {result.errors.map((e, i) => (
                    <div key={i} style={{
                      padding: '6px 10px', background: 'rgba(255, 59, 48, 0.06)',
                      borderRadius: 6, fontSize: 12,
                    }}>
                      <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{e.filename}</span>
                      <span style={{ color: 'var(--text-tertiary)', marginLeft: 8 }}>{e.message}</span>
                    </div>
                  ))}
                </div>
              </section>
            )}
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 20 }}>
              <Space>
                <Button onClick={() => { reset() }}>继续上传</Button>
                <Button type="primary" onClick={close}>完成</Button>
              </Space>
            </div>
          </div>
        ) : (
          // 待上传视图
          <div>
            <div
              style={{
                border: '2px dashed var(--border)',
                borderRadius: 10,
                padding: '40px 20px',
                textAlign: 'center',
                background: 'var(--bg-secondary)',
              }}
            >
              <InboxOutlined style={{ fontSize: 36, color: 'var(--text-tertiary)', marginBottom: 12 }} />
              <div style={{ fontSize: 14, color: 'var(--text-primary)', marginBottom: 4 }}>
                {pending.length} 个文件准备上传
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                支持 .md / .markdown · 解析 frontmatter · 冲突自动重命名
              </div>
            </div>
            <div style={{ marginTop: 12, maxHeight: 200, overflow: 'auto' }}>
              {pending.map((f, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '6px 0', fontSize: 12,
                  borderBottom: '1px solid var(--border-subtle)',
                }}>
                  <FileTextOutlined style={{ color: 'var(--text-tertiary)' }} />
                  <span style={{ color: 'var(--text-primary)' }}>{f.name}</span>
                  <span style={{ color: 'var(--text-tertiary)', marginLeft: 'auto' }}>
                    {(f.size / 1024).toFixed(1)} KB
                  </span>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 20, gap: 8 }}>
              <Button onClick={close} disabled={busy}>取消</Button>
              <Button type="primary" onClick={doUpload} loading={busy}>
                上传 {pending.length} 个
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </>
  )
})
