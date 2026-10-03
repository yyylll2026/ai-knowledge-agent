import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../components/Toast'

export default function Login() {
  const [mode, setMode] = useState('login')   // login | register
  const [form, setForm] = useState({ username: '', email: '', password: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const { login, register } = useAuth()
  const navigate = useNavigate()
  const toast = useToast()

  function update(k, v) {
    setForm((f) => ({ ...f, [k]: v }))
    setError('')
  }

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (mode === 'login') {
        const me = await login(form.username.trim(), form.password)
        toast.success(`欢迎回来，${me.username}`)
        navigate('/chat', { replace: true })
      } else {
        await register({
          username: form.username.trim(),
          email: form.email.trim(),
          password: form.password,
        })
        toast.success('注册成功，请登录')
        setMode('login')
        setForm((f) => ({ ...f, password: '' }))
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-page">
      {/* 背景装饰：两团模糊光晕，让纯暗背景不至于死板 */}
      <div className="glow glow-1" />
      <div className="glow glow-2" />

      <div className="auth-card fade-up">
        <div className="auth-head">
          <div className="auth-mark">AI</div>
          <h1>Knowledge Agent</h1>
          <p>企业级知识库问答 · 检索增强生成</p>
        </div>

        <div className="tabs">
          <button
            className={`tab${mode === 'login' ? ' active' : ''}`}
            onClick={() => { setMode('login'); setError('') }}
            type="button"
          >
            登录
          </button>
          <button
            className={`tab${mode === 'register' ? ' active' : ''}`}
            onClick={() => { setMode('register'); setError('') }}
            type="button"
          >
            注册
          </button>
        </div>

        <form onSubmit={submit} className="auth-form">
          <div className="field">
            <label className="label">
              {mode === 'login' ? '用户名 / 邮箱' : '用户名'}
            </label>
            <input
              className="input"
              value={form.username}
              onChange={(e) => update('username', e.target.value)}
              placeholder={mode === 'login' ? 'lisi 或 you@example.com' : '至少 3 个字符'}
              autoComplete="username"
              required
            />
          </div>

          {mode === 'register' && (
            <div className="field">
              <label className="label">邮箱</label>
              <input
                className="input"
                type="email"
                value={form.email}
                onChange={(e) => update('email', e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
                required
              />
            </div>
          )}

          <div className="field">
            <label className="label">密码</label>
            <input
              className="input"
              type="password"
              value={form.password}
              onChange={(e) => update('password', e.target.value)}
              placeholder={mode === 'register' ? '至少 6 位' : '••••••'}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              required
            />
          </div>

          {error && <div className="form-error">{error}</div>}

          <button className="btn btn-primary btn-block" disabled={busy} type="submit">
            {busy && <span className="spinner" />}
            {busy ? '处理中…' : mode === 'login' ? '登录' : '创建账号'}
          </button>
        </form>

        <div className="auth-foot">
          演示账号 <code>lisi</code> / <code>123456</code>
        </div>
      </div>
    </div>
  )
}
