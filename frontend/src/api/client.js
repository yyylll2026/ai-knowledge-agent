/**
 * 后端 API 封装
 * ------------------------------------------------------------
 * 职责：
 *   1. 统一拼 URL、带 token
 *   2. 统一解析错误（后端错误格式固定是 {"detail": "..."}）
 *   3. token 过期（401）自动登出
 *
 * 为什么不用 axios？
 *   项目只有 6 个接口，fetch 够用，少一个依赖。
 *   但要自己处理"非 2xx 也要读 body"这个坑（见 handleResponse）。
 */

const TOKEN_KEY = 'aka_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}
export function setToken(t) {
  localStorage.setItem(TOKEN_KEY, t)
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

/** 自定义错误，带上 HTTP 状态码，方便上层区分 401 / 400 */
export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** token 失效时通知外层跳登录页（由 AuthProvider 注册） */
let onUnauthorized = null
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn
}

async function handleResponse(res) {
  // 204 之类没有 body 的情况
  const text = await res.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }

  if (!res.ok) {
    // 401 说明 token 过期或无效 —— 清掉 token 并通知外层
    if (res.status === 401) {
      clearToken()
      if (onUnauthorized) onUnauthorized()
    }
    // 后端的错误体统一是 {"detail": "..."}，
    // 但 422（参数校验失败）的 detail 是个数组，要单独处理
    let msg = '请求失败'
    if (data && typeof data === 'object') {
      if (typeof data.detail === 'string') {
        msg = data.detail
      } else if (Array.isArray(data.detail)) {
        msg = data.detail.map((d) => d.msg || '参数错误').join('；')
      }
    } else if (typeof data === 'string' && data) {
      msg = data
    }
    throw new ApiError(msg, res.status)
  }
  return data
}

async function request(path, { method = 'GET', body, formData } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let payload
  if (formData) {
    // 注意：FormData 不能手动设 Content-Type，
    // 浏览器要自己加 multipart 的 boundary
    payload = formData
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }

  let res
  try {
    res = await fetch(path, { method, headers, body: payload })
  } catch {
    // fetch 只有在网络层失败时才 reject（后端没起、断网）
    throw new ApiError('无法连接后端，请确认服务已启动（127.0.0.1:8000）', 0)
  }
  return handleResponse(res)
}

/* ---------------- 认证 ---------------- */

export const authApi = {
  register: (data) =>
    request('/api/v1/auth/register', { method: 'POST', body: data }),
  login: (username, password) =>
    request('/api/v1/auth/login', {
      method: 'POST',
      body: { username, password },
    }),
  me: () => request('/api/v1/auth/me'),
}

/* ---------------- 知识库 ---------------- */

export const kbApi = {
  listDocuments: () => request('/api/v1/knowledge/documents'),

  upload: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return request('/api/v1/knowledge/documents', {
      method: 'POST',
      formData: fd,
    })
  },

  remove: (id) =>
    request(`/api/v1/knowledge/documents/${id}`, { method: 'DELETE' }),

  search: (query, topK = 5) =>
    request('/api/v1/knowledge/search', {
      method: 'POST',
      body: { query, top_k: topK },
    }),

  chat: (question, topK = 3) =>
    request('/api/v1/knowledge/chat', {
      method: 'POST',
      body: { question, top_k: topK },
    }),
}
