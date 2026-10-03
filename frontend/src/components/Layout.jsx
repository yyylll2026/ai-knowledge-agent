import { NavLink, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { useClickOutside } from './Toast'

const NAV = [
  { to: '/chat', label: '知识问答', icon: '◈', desc: 'RAG 对话' },
  { to: '/search', label: '向量检索', icon: '⌕', desc: '查看相似度' },
  { to: '/documents', label: '文档管理', icon: '▤', desc: '上传与删除' },
]

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useClickOutside(() => setMenuOpen(false))

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">AI</div>
          <div className="brand-text">
            <div className="brand-name">Knowledge Agent</div>
            <div className="brand-sub">企业知识智能体</div>
          </div>
        </div>

        <nav className="nav">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-text">
                <span className="nav-label">{item.label}</span>
                <span className="nav-desc">{item.desc}</span>
              </span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-foot">
          <div className="user-chip" ref={menuRef} onClick={() => setMenuOpen((v) => !v)}>
            <div className="avatar">{(user?.username || '?')[0].toUpperCase()}</div>
            <div className="user-meta">
              <div className="user-name">{user?.username}</div>
              <div className="user-mail">{user?.email}</div>
            </div>
            <span className="chev">{menuOpen ? '▴' : '▾'}</span>

            {menuOpen && (
              <div className="user-menu">
                <button
                  className="menu-item"
                  onClick={(e) => {
                    e.stopPropagation()
                    setMenuOpen(false)
                    logout()
                    navigate('/login')
                  }}
                >
                  退出登录
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="mobile-header">
          <div className="mobile-brand">
            <div className="brand-mark">AI</div>
            <div>
              <div className="brand-name">Knowledge Agent</div>
              <div className="brand-sub">企业知识智能体</div>
            </div>
          </div>
          <div className="mobile-account">
            <span className="avatar">{(user?.username || '?')[0].toUpperCase()}</span>
            <span className="mobile-user-name">{user?.username}</span>
            <button
              className="mobile-logout"
              onClick={() => {
                logout()
                navigate('/login')
              }}
            >
              退出
            </button>
          </div>
        </header>
        {children}
      </main>
    </div>
  )
}
