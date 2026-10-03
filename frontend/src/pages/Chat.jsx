import { useState, useRef, useEffect } from 'react'
import { kbApi } from '../api/client'
import { useToast, useCopy } from '../components/Toast'
import { ScoreBar } from '../components/ScoreBar'

const SUGGESTIONS = [
  '出差住宿标准是多少钱？',
  '年假有几天？',
  '加班有加班费吗？',
  '报销需要注意什么？',
]

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [topK, setTopK] = useState(3)
  const scrollRef = useRef(null)
  const composerRef = useRef(null)
  const toast = useToast()
  const copy = useCopy()

  // 新消息进来时滚到底部
  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, busy])

  async function send(question) {
    const q = (question ?? input).trim()
    if (!q || busy) return

    setMessages((m) => [...m, { role: 'user', content: q }])
    setInput('')
    if (composerRef.current) composerRef.current.style.height = 'auto'
    setBusy(true)

    try {
      const res = await kbApi.chat(q, topK)
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: res.answer,
          sources: res.sources || [],
          // 后端在"没有相关资料"时会返回空的 sources，
          // 用它来判断是否命中，比猜文案可靠
          grounded: (res.sources || []).length > 0,
        },
      ])
    } catch (err) {
      toast.error(err.message)
      setInput(q)
      setMessages((m) => [
        ...m,
        { role: 'error', content: err.message },
      ])
    } finally {
      setBusy(false)
    }
  }

  function onKeyDown(e) {
    // Enter 发送，Shift+Enter 换行
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="page chat-page">
      <header className="page-head">
        <div>
          <h1>知识问答</h1>
          <p className="page-sub">
            基于你的文档检索增强生成 · 答案只依据知识库内容
          </p>
        </div>
        <div className="head-controls">
          <label className="inline-label" title="每次喂给大模型的参考段数">
            参考段数
            <select
              className="select"
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
            >
              {[1, 2, 3, 5, 8].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </label>
          {messages.length > 0 && (
            <button className="btn btn-ghost btn-sm" onClick={() => setMessages([])}>
              清空对话
            </button>
          )}
        </div>
      </header>

      <div className="chat-body" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-empty-mark">◈</div>
            <h2>问点什么吧</h2>
            <p>系统会先在你的知识库里检索相关段落，再让模型据此回答；<br />
               如果知识库里没有依据，它会明确告诉你，而不是编造。</p>
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="suggestion" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="msg-list">
            {messages.map((m, i) => (
              <Message
                key={i}
                msg={m}
                onCopy={() => copy(m.content, '回答')}
              />
            ))}
            {busy && (
              <div className="msg msg-assistant fade-up">
                <div className="msg-avatar ai">AI</div>
                <div className="msg-bubble">
                  <div className="thinking">
                    <span className="dot" /><span className="dot" /><span className="dot" />
                    <span className="thinking-text">正在检索知识库并生成回答…</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="composer">
        <div className="composer-box">
          <textarea
            ref={composerRef}
            className="composer-input"
            value={input}
            onChange={(e) => {
              setInput(e.target.value)
              e.currentTarget.style.height = 'auto'
              e.currentTarget.style.height = `${Math.min(e.currentTarget.scrollHeight, 160)}px`
            }}
            onKeyDown={onKeyDown}
            placeholder="输入你的问题…（Enter 发送，Shift+Enter 换行）"
            rows={1}
            maxLength={500}
            aria-label="输入知识库问题"
            disabled={busy}
          />
          <button
            className="btn btn-primary send-btn"
            onClick={() => send()}
            disabled={busy || !input.trim()}
          >
            {busy ? <span className="spinner" /> : '发送'}
          </button>
        </div>
      </div>
    </div>
  )
}

function Message({ msg, onCopy }) {
  const [showSources, setShowSources] = useState(true)

  if (msg.role === 'user') {
    return (
      <div className="msg msg-user fade-up">
        <div className="msg-bubble">{msg.content}</div>
        <div className="msg-avatar me">我</div>
      </div>
    )
  }

  if (msg.role === 'error') {
    return (
      <div className="msg msg-assistant fade-up">
        <div className="msg-avatar err">!</div>
        <div className="msg-bubble msg-error">{msg.content}</div>
      </div>
    )
  }

  return (
    <div className="msg msg-assistant fade-up">
      <div className={`msg-avatar ${msg.grounded ? 'ai' : 'warn'}`}>
        {msg.grounded ? 'AI' : '?'}
      </div>
      <div className="msg-bubble">
        <div className="answer-text">{msg.content}</div>

        <div className="msg-actions">
          <button className="mini-btn" onClick={onCopy}>复制</button>
          {msg.sources?.length > 0 && (
            <button
              className="mini-btn"
              onClick={() => setShowSources((v) => !v)}
            >
              {showSources ? '收起' : '展开'} {msg.sources.length} 条来源
            </button>
          )}
        </div>

        {msg.sources?.length > 0 && showSources && (
          <div className="sources">
            <div className="sources-title">
              引用来源 · {msg.sources.length} 段
            </div>
            {msg.sources.map((s, i) => (
              <SourceCard key={i} source={s} index={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function SourceCard({ source, index }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="source-card">
      <div className="source-head">
        <span className="source-idx">{index + 1}</span>
        <span className="source-file">{source.filename}</span>
        <span className="source-chunk">第 {source.chunk_index} 块</span>
      </div>
      <ScoreBar score={source.score} />
      {source.content && (
        <>
          <div className={`source-preview${open ? ' open' : ''}`}>
            {source.content}
          </div>
          <button className="link-btn" onClick={() => setOpen((v) => !v)}>
            {open ? '收起' : '查看原文'}
          </button>
        </>
      )}
    </div>
  )
}
