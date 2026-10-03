import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ToastProvider } from './components/Toast'
import Layout from './components/Layout'
import Login from './pages/Login'
import Chat from './pages/Chat'
import Search from './pages/Search'
import Documents from './pages/Documents'
import './styles/theme.css'
import './styles/app.css'

/** 需要登录才能进的页面包一层 */
function Protected({ children }) {
  const { user, loading } = useAuth()

  // 关键：恢复会话是异步的（要拿本地 token 去问后端）。
  // 不加这个 loading 判断的话，刷新页面会先闪一下登录页。
  if (loading) {
    return (
      <div className="boot">
        <span className="spinner" />
        <span>正在恢复会话…</span>
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  return <Layout>{children}</Layout>
}

function PublicOnly({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="boot"><span className="spinner" /></div>
  if (user) return <Navigate to="/chat" replace />
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
            <Route path="/chat" element={<Protected><Chat /></Protected>} />
            <Route path="/search" element={<Protected><Search /></Protected>} />
            <Route path="/documents" element={<Protected><Documents /></Protected>} />
            <Route path="*" element={<Navigate to="/chat" replace />} />
          </Routes>
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  )
}
