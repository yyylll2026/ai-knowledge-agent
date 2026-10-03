import { useState, useEffect, useRef, useCallback } from 'react'
import { kbApi } from '../api/client'
import { useToast } from '../components/Toast'

const ACCEPT = ['.txt', '.md', '.markdown']

function fmtSize(bytes) {
  if (!bytes) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

function fmtTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export default function Documents() {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState([])   // [{name, pct}]
  const [dragging, setDragging] = useState(false)
  const [pendingDelete, setPendingDelete] = useState(null)
  const fileRef = useRef(null)
  const toast = useToast()

  const load = useCallback(async () => {
    try {
      const res = await kbApi.listDocuments()
      setDocs(res.items || [])
    } catch (err) {
      toast.error(err.message)
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => { load() }, [load])

  const handleFiles = useCallback(
    async (fileList) => {
      const files = Array.from(fileList || [])
      if (!files.length) return

      for (const file of files) {
        const ext = '.' + (file.name.split('.').pop() || '').toLowerCase()
        if (!ACCEPT.includes(ext)) {
          toast.error(`「${file.name}」格式不支持，仅接受 ${ACCEPT.join(' / ')}`)
          continue
        }
        setUploading((u) => [...u, { name: file.name }])
        try {
          const res = await kbApi.upload(file)
          const chunks = res.meta?.chunk_count ?? 0
          toast.success(`「${file.name}」上传成功，切分为 ${chunks} 块`)
        } catch (err) {
          toast.error(`「${file.name}」上传失败：${err.message}`)
        } finally {
          setUploading((u) => u.filter((x) => x.name !== file.name))
        }
      }
      load()
    },
    [load, toast]
  )

  async function confirmDelete() {
    const doc = pendingDelete
    setPendingDelete(null)
    try {
      const res = await kbApi.remove(doc.id)
      toast.success(`已删除「${doc.filename}」（移除 ${res.chunks_removed} 块向量）`)
      load()
    } catch (err) {
      toast.error(err.message)
    }
  }

  const totalChunks = docs.reduce((s, d) => s + (d.meta?.chunk_count || 0), 0)
  const totalChars = docs.reduce((s, d) => s + (d.meta?.char_count || 0), 0)

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>文档管理</h1>
          <p className="page-sub">
            上传的文档会被切块、向量化，并同步写入向量库
          </p>
        </div>
      </header>

      <div className="stats">
        <Stat label="文档" value={docs.length} />
        <Stat label="文本块" value={totalChunks} />
        <Stat label="总字数" value={totalChars.toLocaleString()} />
      </div>

      {/* 拖拽上传区 */}
      <div
        className={`dropzone${dragging ? ' dragging' : ''}`}
        role="button"
        tabIndex={0}
        aria-label="选择要上传的文档"
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            fileRef.current?.click()
          }
        }}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          handleFiles(e.dataTransfer.files)
        }}
        onClick={() => fileRef.current?.click()}
      >
        <input
          ref={fileRef}
          type="file"
          multiple
          accept={ACCEPT.join(',')}
          style={{ display: 'none' }}
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => {
            handleFiles(e.target.files)
            e.target.value = ''   // 允许重复上传同一个文件
          }}
        />
        <div className="dropzone-icon">⇪</div>
        <div className="dropzone-title">
          {dragging ? '松开即可上传' : '拖拽文件到此处，或点击选择'}
        </div>
        <div className="dropzone-hint">
          支持 {ACCEPT.join(' / ')} · 文本会用 UTF-8 / GBK 自动识别编码
        </div>
      </div>

      {uploading.length > 0 && (
        <div className="uploading">
          {uploading.map((u) => (
            <div key={u.name} className="uploading-item">
              <span className="spinner" />
              <span>正在处理「{u.name}」…（调用向量化接口，可能需要几秒）</span>
            </div>
          ))}
        </div>
      )}

      <div className="doc-section-title">已上传文档</div>

      {loading ? (
        <div className="placeholder"><span className="spinner" /> 加载中…</div>
      ) : docs.length === 0 ? (
        <div className="placeholder">
          <div className="placeholder-mark">▤</div>
          <p>还没有上传任何文档</p>
        </div>
      ) : (
        <div className="doc-table">
          <div className="doc-row doc-head">
            <span>文件名</span>
            <span>类型</span>
            <span>块数</span>
            <span>字数</span>
            <span>上传时间</span>
            <span />
          </div>
          {docs.map((d) => (
            <div key={d.id} className="doc-row">
              <span className="doc-name" title={d.filename}>{d.filename}</span>
              <span><span className="tag">{d.file_type}</span></span>
              <span className="doc-num">{d.meta?.chunk_count ?? '—'}</span>
              <span className="doc-num">{(d.meta?.char_count ?? 0).toLocaleString()}</span>
              <span className="doc-time">{fmtTime(d.created_at)}</span>
              <span className="doc-actions">
                <button
                  className="btn btn-danger btn-sm"
                  onClick={() => setPendingDelete(d)}
                >
                  删除
                </button>
              </span>
            </div>
          ))}
        </div>
      )}

      {pendingDelete && (
        <div className="modal-mask" onClick={() => setPendingDelete(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>确认删除</h3>
            <p>
              将删除「<strong>{pendingDelete.filename}</strong>」，以及它的{' '}
              <strong>{pendingDelete.meta?.chunk_count ?? 0}</strong> 个文本块和对应向量。
              此操作不可撤销。
            </p>
            <div className="modal-actions">
              <button className="btn btn-ghost" onClick={() => setPendingDelete(null)}>
                取消
              </button>
              <button className="btn btn-danger" onClick={confirmDelete}>
                确认删除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div className="stat card">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}
