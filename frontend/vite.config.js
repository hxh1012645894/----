import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '',
  server: {
    port: 5175,
    host: true,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        timeout: 300000,
      },
      '/uploads': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        timeout: 300000,
      }
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    assetsDir: 'assets'
  },
  optimizeDeps: {
    exclude: ['vue-demi']
  }
})
