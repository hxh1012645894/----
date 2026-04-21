// 从环境变量读取后端服务地址
// 支持两种配置方式：
// 1. 分开配置: VITE_BACKEND_HOST + VITE_BACKEND_PORT
// 2. 直接配置完整 URL: VITE_BACKEND_URL (优先使用)

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL
const API_HOST = import.meta.env.VITE_BACKEND_HOST || '127.0.0.1'
const API_PORT = import.meta.env.VITE_BACKEND_PORT || '8000'

// 如果配置了完整 URL，优先使用
export const BASE_URL = BACKEND_URL || `http://${API_HOST}:${API_PORT}`
