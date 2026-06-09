import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3077,
    strictPort: true,  // 端口冲突时直接 fail, 不静默回退 3000
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      // 已发布站点静态资源 (P1-UI-4 站点作品集"立即查看"打开 /docs/.../index.html)
      // 不代理会让 Vite SPA fallback 返回 index.html, 然后 React Router 不认跳 /
      '/docs': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        // BUG-14: 重 build 后浏览器缓存, 不强刷见不到新 JS, 加 no-cache
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0',
        },
      },
    },
  },
  build: {
    outDir: 'dist',
  },
})
