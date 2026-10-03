import { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react'

const ToastContext = createContext(null)

/**
 * 轻量提示条。
 * 为什么不用 window.alert？—— 它会阻塞整个页面，而且丑。
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const idRef = useRef(0)

  const push = useCallback((message, type = 'info', duration = 3200) => {
    const id = ++idRef.current
    setToasts((t) => [...t, { id, message, type }])
    setTimeout(() => {
      setToasts((t) => t.filter((x) => x.id !== id))
    }, duration)
    return id
  }, [])

  const api = {
    info: (m) => push(m, 'info'),
    success: (m) => push(m, 'success'),
    error: (m) => push(m, 'error', 5000),
  }

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="toast-stack">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.type}`}>
            <span className="toast-icon">
              {t.type === 'success' ? '✓' : t.type === 'error' ? '!' : 'i'}
            </span>
            <span>{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast 必须在 ToastProvider 内使用')
  return ctx
}

/** 复制到剪贴板，带降级方案（http 环境下 navigator.clipboard 不可用） */
export function useCopy() {
  const toast = useToast()
  return useCallback(
    async (text, label = '内容') => {
      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(text)
        } else {
          // 降级：临时 textarea + execCommand
          const ta = document.createElement('textarea')
          ta.value = text
          ta.style.position = 'fixed'
          ta.style.opacity = '0'
          document.body.appendChild(ta)
          ta.select()
          document.execCommand('copy')
          document.body.removeChild(ta)
        }
        toast.success(`${label}已复制`)
      } catch {
        toast.error('复制失败')
      }
    },
    [toast]
  )
}

/** 点击外部关闭（下拉菜单等） */
export function useClickOutside(onClose) {
  const ref = useRef(null)
  useEffect(() => {
    function handler(e) {
      if (ref.current && !ref.current.contains(e.target)) onClose()
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [onClose])
  return ref
}
