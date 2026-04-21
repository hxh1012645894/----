import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 读取环境变量
const API_HOST = process.env.VITE_BACKEND_HOST || '127.0.0.1'
const API_PORT = process.env.VITE_BACKEND_PORT || '8000'

export default defineConfig({
  plugins: [vue()],
  base: '',
  server: {
    port: 5173,
    host: true,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: `http://${API_HOST}:${API_PORT}`,
        changeOrigin: true,
        timeout: 300000,
      },
      '/uploads': {
        target: `http://${API_HOST}:${API_PORT}`,
        changeOrigin: true,
        timeout: 300000,
      }
    }
  },
  build: {
    outDir: '../static',
    emptyOutDir: true,
    assetsDir: 'assets'
  },
  // 解决 node_modules 中的弃用警告
  optimizeDeps: {
    exclude: ['vue-demi']
  }
})
