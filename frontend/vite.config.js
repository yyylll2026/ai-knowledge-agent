import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 开发时前端跑在 5173，后端在 8000。
// 这里配一个代理：前端只请求 /api/... （同源），由 Vite 转发到后端。
// 好处是开发期浏览器根本不认为跨域，连 CORS 预检都不会发。
//
// 注意：后端的 CORS 中间件仍然保留 —— 生产环境（前端静态文件单独部署）
// 没有这层代理，就得靠 CORS。两条路都留着。
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
