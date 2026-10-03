import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { authApi, getToken, setToken, clearToken, setUnauthorizedHandler } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // token 过期时（client.js 里检测到 401）自动清空登录态
  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null))
  }, [])

  // 刷新页面后：localStorage 里还有 token 就试着恢复会话
  // 注意必须校验 token 还有效（可能已过期），不能直接信任本地存的
  useEffect(() => {
    let cancelled = false
    async function restore() {
      if (!getToken()) {
        setLoading(false)
        return
      }
      try {
        const me = await authApi.me()
        if (!cancelled) setUser(me)
      } catch {
        clearToken()   // token 失效，清掉
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    restore()
    return () => { cancelled = true }
  }, [])

  const login = useCallback(async (username, password) => {
    const { access_token } = await authApi.login(username, password)
    setToken(access_token)
    const me = await authApi.me()
    setUser(me)
    return me
  }, [])

  const register = useCallback(async (data) => {
    // 注册完不自动登录 —— 让用户明确走一次登录，符合直觉
    return authApi.register(data)
  }, [])

  const logout = useCallback(() => {
    clearToken()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth 必须在 AuthProvider 内使用')
  return ctx
}
