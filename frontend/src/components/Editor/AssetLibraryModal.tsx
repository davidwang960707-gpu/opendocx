import { useEffect, useRef, useState } from 'react'
import { Button, Empty, Modal, Popconfirm, Spin, Tag, Tooltip, message } from 'antd'
import {
  DeleteOutlined,
  FileOutlined,
  InboxOutlined,
  PaperClipOutlined,
  PictureOutlined,
  PlusOutlined,
} from '@ant-design/icons'
import { assetApi } from '../../services/api'
import type { DocumentAsset } from '../../types/api'

interface Props {
  open: boolean
  versionId: string
  onClose: () => void
  onInsert: (markdown: string) => void
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function iconFor(asset: DocumentAsset) {
  if (asset.kind === 'image') return <PictureOutlined />
  if (asset.kind === 'video') return <PaperClipOutlined />
  return <FileOutlined />
}

export default function AssetLibraryModal({ open, versionId, onClose, onInsert }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [assets, setAssets] = useState<DocumentAsset[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)

  const loadAssets = async () => {
    if (!versionId) return
    setLoading(true)
    try {
      const res = await assetApi.list(versionId)
      setAssets(res.data.data || [])
    } catch (e: any) {
      message.error(`加载资产失败: ${e.response?.data?.detail || e.message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open) loadAssets()
  }, [open, versionId])

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    setUploading(true)
    try {
      const uploaded: DocumentAsset[] = []
      for (const file of Array.from(files)) {
        const res = await assetApi.upload(versionId, file)
        uploaded.push(res.data.data)
      }
      message.success(`已上传 ${uploaded.length} 个资产`)
      setAssets(prev => [...uploaded, ...prev])
    } catch (e: any) {
      message.error(`上传失败: ${e.response?.data?.detail || e.message}`)
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const handleDelete = async (asset: DocumentAsset) => {
    try {
      await assetApi.delete(asset.id)
      setAssets(prev => prev.filter(item => item.id !== asset.id))
      message.success('已删除资产')
    } catch (e: any) {
      message.error(`删除失败: ${e.response?.data?.detail || e.message}`)
    }
  }

  return (
    <Modal
      open={open}
      onCancel={onClose}
      title="文档资产库"
      width={860}
      footer={[
        <Button key="upload" icon={<PlusOutlined />} loading={uploading} onClick={() => inputRef.current?.click()}>
          上传图片/附件
        </Button>,
        <Button key="close" type="primary" onClick={onClose}>完成</Button>,
      ]}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".png,.jpg,.jpeg,.gif,.webp,.mp4,.webm,.mov,.pdf,.zip,.txt,.csv,.xlsx,.docx,.pptx"
        style={{ display: 'none' }}
        onChange={(e) => handleFiles(e.target.files)}
      />

      <div style={{
        border: '1px dashed var(--border)',
        borderRadius: 10,
        padding: '14px 16px',
        marginBottom: 16,
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        background: 'var(--bg-secondary)',
        color: 'var(--text-secondary)',
      }}>
        <InboxOutlined style={{ color: 'var(--brand-primary)' }} />
        <span>上传后点击“插入”会写入 Markdown。图片发布时会被复制到静态站 assets 目录。</span>
      </div>

      {loading ? (
        <div style={{ padding: 48, textAlign: 'center' }}><Spin /></div>
      ) : assets.length === 0 ? (
        <Empty description="还没有上传图片或附件" />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, maxHeight: 520, overflow: 'auto', paddingRight: 4 }}>
          {assets.map(asset => (
            <div key={asset.id} style={{
              border: '1px solid var(--border-subtle)',
              borderRadius: 10,
              background: 'var(--bg-primary)',
              overflow: 'hidden',
            }}>
              <div style={{
                height: 132,
                background: 'var(--bg-secondary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--text-tertiary)',
              }}>
                {asset.kind === 'image' ? (
                  <img
                    src={asset.file_url}
                    alt={asset.original_filename}
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  />
                ) : (
                  <div style={{ textAlign: 'center', fontSize: 28 }}>
                    {iconFor(asset)}
                  </div>
                )}
              </div>
              <div style={{ padding: 12 }}>
                <Tooltip title={asset.original_filename}>
                  <div style={{
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    marginBottom: 8,
                  }}>
                    {asset.original_filename}
                  </div>
                </Tooltip>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                  <Tag style={{ margin: 0 }}>{asset.kind}</Tag>
                  <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{formatSize(asset.size_bytes)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                  <Button size="small" type="primary" onClick={() => onInsert(asset.markdown)}>
                    插入
                  </Button>
                  <Popconfirm title="删除这个资产？" description="已插入文档的引用不会自动清理。" onConfirm={() => handleDelete(asset)}>
                    <Button size="small" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </Modal>
  )
}
