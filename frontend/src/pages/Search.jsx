import { useState } from 'react'
import { kbApi } from '../api/client'
import { useToast, useCopy } from '../components/Toast'
import { ScoreBar, EmptyResult, scoreTier } from '../components/ScoreBar'

export default function Search() {
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(5)
  const [hits, setHits] = useState(null)   // null=还没搜过, []=搜过但没结果
  const [busy, setBusy] = useState(false)
  const [lastQuery, setLastQuery] = useState('')
  const toast = useToast()
  const copy = useCopy()

  async function run(e) {
    e?.preventDefault()
    const q = query.trim()
    if (!q || busy) return
    setBusy(true)
    try {
      const res = await kbApi.search(q, topK)
      setHits(res.hits || [])
      setLastQuery(q)
    } catch (err) {
      toast.error(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>向量检索</h1>
          <p className="page-sub">
            直接查看知识库的检索结果与相似度分布，不走大模型
          </p>
        </div>
      </header>

      <form className="search-bar" onSubmit={run}>
        <input
          className="input search-input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="输入查询语句，例如：住宿标准是多少"
        />
        <label className="inline-label">
          top_k
          <select
            className="select"
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
          >
            {[3, 5, 10, 20].map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </label>
        <button className="btn btn-primary" disabled={busy || !query.trim()}>
          {busy ? <span className="spinner" /> : '检索'}
        </button>
      </form>

      {hits === null && (
        <div className="placeholder">
          <div className="placeholder-mark">⌕</div>
          <p>输入查询语句，查看向量检索返回的原始结果</p>
          <div className="legend">
            <span className="legend-item"><i className="sw sw-high" />高相关 ≥ 0.55</span>
            <span className="legend-item"><i className="sw sw-mid" />达标 ≥ 0.46</span>
            <span className="legend-item"><i className="sw sw-low" />低于阈值</span>
            <span className="legend-item"><i className="sw sw-line" />阈值线 0.46</span>
          </div>
        </div>
      )}

      {hits !== null && hits.length === 0 && (
        <EmptyResult query={lastQuery} topK={topK} />
      )}

      {hits !== null && hits.length > 0 && (
        <>
          <div className="result-meta">
            共 <strong>{hits.length}</strong> 条结果 · 查询「{lastQuery}」
            <span className="meta-hint">
              （低于阈值 0.46 的已在后端被过滤，所以这里看到的都是达标的）
            </span>
          </div>
          <div className="hit-list">
            {hits.map((h, i) => (
              <HitCard key={h.chunk_id} hit={h} rank={i + 1} onCopy={copy} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function HitCard({ hit, rank, onCopy }) {
  const [expanded, setExpanded] = useState(false)
  const tier = scoreTier(hit.score)
  const isLong = hit.content.length > 220
  const shown = expanded || !isLong ? hit.content : hit.content.slice(0, 220) + '…'

  return (
    <div className={`hit-card fade-up tier-${tier}`}>
      <div className="hit-head">
        <span className="hit-rank">#{rank}</span>
        <span className="hit-file">{hit.filename}</span>
        <span className="hit-chunk">第 {hit.chunk_index} 块</span>
        <span className="hit-spacer" />
        <button className="mini-btn" onClick={() => onCopy(hit.content, '原文')}>
          复制
        </button>
      </div>

      <ScoreBar score={hit.score} />

      <div className="hit-content">{shown}</div>

      {isLong && (
        <button className="link-btn" onClick={() => setExpanded((v) => !v)}>
          {expanded ? '收起' : '展开全文'}
        </button>
      )}

      <div className="hit-foot">
        <span>chunk_id {hit.chunk_id}</span>
        <span>document_id {hit.document_id}</span>
      </div>
    </div>
  )
}
